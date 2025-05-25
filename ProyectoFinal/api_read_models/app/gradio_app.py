import gradio as gr
import requests

API_URL = "http://10.43.101.170:45101"  # Servicio FastAPI en docker-compose

def get_models():
    try:
        r = requests.get(f"{API_URL}/models")
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return [f"❌ Error al obtener modelos: {str(e)}"]

def predict(model_name,feature_1,feature_2,feature_3,feature_4,feature_5,feature_6,feature_7,feature_8,
        feature_9,feature_10,feature_11,feature_12,feature_13,feature_14,feature_15 
               ):
    
    payload = {
        "feature_1": int(feature_1),
        "feature_2": int(feature_2),
        "feature_3": int(feature_3),
        "feature_4": int(feature_4),
        "feature_5": int(feature_5),
        "feature_6": int(feature_6),
        "feature_7": int(feature_7),
        "feature_8": int(feature_8),
        "feature_9": int(feature_9),
        "feature_10": int(feature_10),
        "feature_11": int(feature_11),
        "feature_12": int(feature_12),
        "feature_13": int(feature_13),
        "feature_14": int(feature_14),
        "feature_15": int(feature_15)
    }

    try:
        r = requests.post(f"{API_URL}/predict/{model_name.split(":")[0]}", json=payload)
        r.raise_for_status()
        return r.json().get("predictions", "Sin predicción")
    except Exception as e:
        return f"❌ Error para {model_name}: {str(e)}"

def update_model_choices():
    return gr.update(choices=get_models())

with gr.Blocks() as demo:
    gr.Markdown("# 🧠 Predicción con Modelos MLflow")
    gr.Markdown("Selecciona un modelo, completa los datos y obtén una predicción.")

    with gr.Row():
        model_dropdown = gr.Dropdown(choices=get_models(), label="Modelo", interactive=True)
        reload_button = gr.Button("🔄 Recargar Modelos")
        reload_button.click(fn=update_model_choices, outputs=model_dropdown)

    with gr.Row():
        input_fields = [
            model_dropdown,
            gr.Number(label="feature_1"),
            gr.Number(label="feature_2"),
            gr.Number(label="feature_3"),
            gr.Number(label="feature_4"),
            gr.Number(label="feature_5"),
            gr.Number(label="feature_6"),
            gr.Number(label="feature_7"),
            gr.Number(label="feature_8"),
            gr.Number(label="feature_9"),
            gr.Number(label="feature_10"),
            gr.Number(label="feature_11"),
            gr.Number(label="feature_12"),
            gr.Number(label="feature_13"),
            gr.Number(label="feature_14"),
            gr.Number(label="feature_15")
        ]
    
    output = gr.Textbox(label="📈 Predicción")

    submit_btn = gr.Button("🚀 Predecir")
    submit_btn.click(fn=predict, inputs=input_fields, outputs=output)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)