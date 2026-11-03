from datetime import datetime

formats = ["%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"]
date_text =  input("Enter date : ")
date_obj =  None
for fmt in formats:
        try:
            date_obj  = datetime.strptime(date_text, fmt)
            break
        except ValueError:
            continue
if date_obj is None:
        print("Invalid date! Please enter the date again.")
date_text = date_obj.strftime("%Y-%m-%d")

print("month = ", date_obj.month)
