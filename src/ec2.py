import boto3
import os
import sys
from tabulate import tabulate
import utils

class Ec2Helper:
    def __init__(self, profile, region, keyFolder, filters):
        self.profile = profile
        self.region = region
        self.keyFolder = keyFolder
        self.all_instances = []
        self.instances = []
        self.chosen_instance = None
        self.filters = filters
        self.session=boto3.Session(profile_name = self.profile if self.profile else None, region_name=self.region)

    def start(self):
        # Continuously prompt the user to select an EC2 instance and an action to perform
        while True:
            self.getEc2Instances()
            self.ec2ActionPrompt()
        return

    def startSsmSession(self):
        # Start an SSM session with the chosen EC2 instance
        print(f"Starting ssm session with instance - {self.chosen_instance['Name']} - {self.chosen_instance['InstanceId']}")
        # Use os.system to execute a command in the shell, creating an SSM session with the appropriate instance ID, region, and profile
        command = f"aws ssm start-session {f'--profile {self.profile}' if self.profile else ''} --target {self.chosen_instance['InstanceId']} --region {self.chosen_instance['Az'][:-1]}"
        os.system(command)
        return

    def startSshSession(self,loginType):
        # Start an SSH session with the chosen EC2 instance
        instanceId=self.chosen_instance['InstanceId']
        keyName=self.chosen_instance["KeyName"]
        # Prompt the user to enter the username to use when connecting to the instance over SSH
        user= input(f"Ec2 instance user to connect to [ec2-user]: ") or "ec2-user"
        if loginType == "key":
            # Prompt the user to enter the subfolder in which their SSH keys are stored
            key_subfolder= input(f"Ssh keys subfolder name inside {self.keyFolder}. [None]: ") 
        # Determine whether to connect via public or private IP address, based on which is available
        if self.chosen_instance['PrivateIpAddress'] and self.chosen_instance['PublicIpAddress']:
            print("Choose one:")
            print("1 - SSH to PrivateIp")
            print("2 - SSH to PublicIp")
            choice = utils.choiceEvaluator([2])
            usePrivate = True if int(choice) == 1 else False 
        elif self.chosen_instance['PrivateIpAddress']:
            usePrivate = True
        elif self.chosen_instance['PublicIpAddress']:
            usePrivate = False  
        ip=self.chosen_instance[f"{'Private' if usePrivate else 'Public'}IpAddress"]
        # Use os.system to execute an SSH command in the shell, connecting to the chosen instance with the correct authentication method and IP address
        print(f"Starting ssh session with instance - {self.chosen_instance['Name']} - {instanceId} - {user}@{ip} - {f'using ssh key {self.keyFolder}/{key_subfolder}/{keyName}' if loginType == 'key' else 'with password authentication'}")
        command=f"ssh {f'-i {self.keyFolder}/{key_subfolder}/{keyName}' if loginType == 'key' else ''} {user}@{ip}"
        os.system(command)
        return

    def getEc2Instances(self, refresh=True):
        # Retrieve a list of all EC2 instances associated with the user's account
        if refresh:
            ec2 = self.session.client('ec2')
            # Use the describe_instances method to obtain a list of all EC2 instances
            response = ec2.describe_instances()
            # Store relevant information about each instance in a list of dictionaries
            self.all_instances = [{
                "Index"             : i+1,
                "Name"              : inst.get("Tags", [{"Value": None}],)[0]["Value"],
                "InstanceId"        : inst["InstanceId"],
                "InstanceType"      : inst["InstanceType"],
                "KeyName"           : inst.get("KeyName"),
                "VpcId"             : inst["VpcId"],
                "SubnetId"          : inst["SubnetId"],
                "Az"                : inst["Placement"]["AvailabilityZone"],
                "PrivateIpAddress"  : inst["PrivateIpAddress"],
                "PublicIpAddress"   : inst.get("PublicIpAddress"),
                "State"             : inst["State"]["Name"]
                } for i, res in enumerate(response["Reservations"]) for inst in res["Instances"]]      
        # Filter the list of instances to only include those that match the user's filter criteria
        self.filterInstances()
        # Present the user with a prompt to select one of the filtered instances
        self.ec2ListPrompt()
        return


    def ec2ActionPrompt(self):
        # Print a header for the action prompt
        print("######################################## Action")
        # Print information about the selected instance
        print("Selected Instance")
        print(tabulate([self.chosen_instance], headers="keys", tablefmt="grid", maxcolwidths=[None,20]))
        # Present the user with action options
        print("Choose one Action:")
        print("1) SSM session")
        print("2) SSH with Key")
        print("3) SSH with Password")
        print("q) to Quit")
        print("b) to go Back")
        # Evaluate the user's input using the utils module
        choice = utils.choiceEvaluator([3,"b","q"])
        # Execute the appropriate action based on the user's choice
        if choice == "q":
            sys.exit()
        elif choice == "b":
            return 
        elif int(choice) == 1:
            self.startSsmSession()
        elif int(choice) == 2:
            # Start an SSH session with key authentication
            self.startSshSession("key")
        elif int(choice) == 3:
            # Start an SSH session with password authentication
            self.startSshSession("password")

    def ec2ListPrompt(self):
        # Print a header for the EC2 list
        print("######################################## EC2 List")
        # Print the active filters
        print(f"Active Filters: {self.filters}")
        # Print the list of instances using tabulate module
        print(tabulate(self.instances, headers="keys", tablefmt="grid", maxcolwidths=[None,20]))
        # Print the options for the user to choose from
        print("Type: ")
        print('f) to change filters')
        print('r) to reload instances list')
        print('q) to Quit')
        print("Or select an instance Index to connect") 
        # Evaluate the user's input using the utils module
        choice = utils.choiceEvaluator([len(self.instances),"f","q","r"])
        # Execute the appropriate action based on the user's choice
        if choice == "f":
            self.changeFilters()
        elif choice == "q":
            sys.exit()
        elif choice == "r":
            self.getEc2Instances()
        elif int(choice) in range(len(self.instances)+1):
            # Set the chosen_instance attribute to the selected instance
            self.chosen_instance=self.instances[int(choice)-1]
        return 
    
    def filterInstances(self):
        # Make a copy of the list of all instances
        self.instances = [inst for inst in self.all_instances]
        # If there are no filters, return the unfiltered list of instances
        if not self.filters:
            return

        # Iterate over each filter 
        for filter_name, filter_value in self.filters:
            # Filter out any instances that do not have the specified filter key or whose value does not contain the specified filter value
            self.instances = [inst for inst in self.instances if inst.get(filter_name) and filter_value in inst[filter_name]]
    
    def changeFilters(self):
        # Print out a heading for the menu
        print("######################################## Filters")
        # Display the list of current filters
        self.showFilters()
        # Print out the menu options
        print("Type:")
        print('a) to add filters')
        print('b) to go back')
        print('q) to quit')
        # If there are active filters, provide an additional option to remove filters
        if self.filters:
            print("Or insert a filter index to remove it")

        # Wait for user input and get their choice using the `choiceEvaluator` function from the `utils` module
        choice = utils.choiceEvaluator([len(self.filters) if self.filters else None, "a", "b", "q"])
        print(choice)

        # Depending on the user's choice, carry out the appropriate action
        if choice == "a":
            # Prompt the user to enter a new filter and add it to the filters list
            new_filter = input("Insert filter (format key:value): ")
            if not self.filters:
                self.filters = []
            self.filters.append((new_filter.split(":")[0], new_filter.split(":")[1]))
            # Call this function again to display the updated list of filters
            self.changeFilters()

        elif choice == "b":
            # Go back to the previous menu by calling the `getEc2Instances` function
            self.getEc2Instances(refresh=False)

        elif choice == "q":
            # Exit the program using the `sys` module
            sys.exit()

        elif int(choice) in range(1, len(self.filters) + 1):
            # Remove the filter at the specified index and call this function again to display the updated list of filters
            del self.filters[int(choice)-1]
            self.changeFilters()
    
    def showFilters(self):
        # Check if there are any active filters
        if self.filters:
            # Print out a heading for the list of active filters
            print("Active filters:")
            # Iterate over each filter in the filters list
            for index, filter in enumerate(self.filters, 1):
                # Print out the filter and its corresponding index
                print(f"{index}) {filter}")
        else:
            # If there are no active filters, print out a message indicating so
            print("No active filters")