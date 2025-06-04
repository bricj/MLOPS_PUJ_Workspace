import gradio as gr
import requests

API_URL = "http://10.43.101.170:45101"

def get_models():
    try:
        r = requests.get(f"{API_URL}/models")
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return []

def get_input_schema(model_name):
    try:
        model_id = model_name.split(":")[0]
        r = requests.get(f"{API_URL}/model/get-schema", params={"model_name": model_id})
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {}

def create_input_components(schema: dict):
    components = []
    for name, dtype in schema.items():
        if dtype in ("float", "int"):
            components.append(gr.Number(label=name))
        else:
            components.append(gr.Textbox(label=name))
    return components

def predict(model_name, *values):
    try:
        model_id = model_name.split(":")[0]
        schema = get_input_schema(model_name)
        payload = {}

        for (key, dtype), value in zip(schema.items(), values):
            if dtype == "float":
                payload[key] = float(value)
            elif dtype == "int":
                payload[key] = int(value)
            else:
                payload[key] = str(value)

        r = requests.post(f"{API_URL}/predict/{model_id}", json=payload)
        r.raise_for_status()
        return r.json().get("predictions", "Sin predicción")
    except Exception as e:
        return f"❌ Error en la predicción: {str(e)}"

with gr.Blocks() as demo:
    gr.Markdown("# 🧠 Predicción con Modelos MLflow")

    with gr.Row():
        model_dropdown = gr.Dropdown(label="Modelo", interactive=True)
        reload_button = gr.Button("🔄 Recargar Modelos")

    input_container = gr.Column()
    prediction_output = gr.Textbox(label="📈 Predicción")
    submit_btn = gr.Button("🚀 Predecir")

    def init_models():
        models = get_models()
        return gr.update(choices=models, value=models[0] if models else None)

    def update_inputs_and_bind_prediction(model_name):
        schema = get_input_schema(model_name)
        inputs = create_input_components(schema)

        # Limpiar contenedor y agregar inputs
        input_container.children = inputs

        # Reconectar botón de predicción
        submit_btn.click(
            fn=predict,
            inputs=[model_dropdown, *inputs],
            outputs=prediction_output,
            show_progress=False,
        )
        return inputs

    # Cargar modelos al iniciar
    demo.load(fn=init_models, outputs=model_dropdown).then(
        fn=update_inputs_and_bind_prediction,
        inputs=model_dropdown,
        outputs=input_container,
    )

    # Cuando se cambia de modelo manualmente
    model_dropdown.change(
        fn=update_inputs_and_bind_prediction,
        inputs=model_dropdown,
        outputs=input_container,
    )

    # Recargar modelos manualmente
    reload_button.click(fn=init_models, outputs=model_dropdown)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)