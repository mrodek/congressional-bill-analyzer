import traceback
import sys

try:
    from src.app import create_interface
    app = create_interface()
    app.launch()
except Exception as e:
    with open('error_log.txt', 'w') as f:
        f.write(f'Error: {str(e)}\n\n{traceback.format_exc()}')
    print(f"Error occurred: {str(e)}")
    print("Full error details written to error_log.txt")
