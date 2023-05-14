def choiceEvaluator(options):
    while True:
        choice = input("Your choice: ")
        try:
            choice = int(choice)
            if choice in range(1, options[0]+1):
                break
            else:
                print("That's not a valid choice. Please try again and insert a valid index.")
        except ValueError:
            if choice in options[1:]:
                break
            else:
                print("That's not a valid choice. Please try again and insert a valid index.")
    return choice