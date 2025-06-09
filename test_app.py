import gradio as gr

def greet(name):
    print(f"DEBUG: greet function called with name: {name}")
    return "Hello, " + name + "!"

with gr.Blocks() as demo:
    name_input = gr.Textbox(label="Enter your name")
    output_text = gr.Textbox(label="Greeting")
    greet_btn = gr.Button("Greet")

    greet_btn.click(fn=greet, inputs=name_input, outputs=output_text)

if __name__ == "__main__":
    print("Launching minimal test app...")
    demo.launch(debug=True) # Using debug=True for more verbose FastAPI/Starlette logs if needed
