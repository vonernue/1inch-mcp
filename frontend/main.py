import gradio as gr

# Dummy chatbot function
def chat_bot(message, history):
    return f"Echo: {message}"

# Dummy settings save function
def save_settings(api_key, username):
    return f"Settings saved! (username: {username})"

with gr.Blocks(title="Gradio App with Tabs") as app:
    with gr.Tabs():
        # Settings Tab
        with gr.Tab("🔧 Settings"):
            gr.Markdown("## App Settings")

            api_key = gr.Textbox(label="API Key", type="password")
            username = gr.Textbox(label="Username")
            save_btn = gr.Button("Save Settings")
            settings_output = gr.Textbox(label="Status", interactive=False)

            save_btn.click(
                fn=save_settings,
                inputs=[api_key, username],
                outputs=settings_output
            )

        # Chat Tab
        with gr.Tab("💬 Chat"):
            gr.Markdown("## Chat with the Assistant")
            gr.ChatInterface(fn=chat_bot)

app.launch()
