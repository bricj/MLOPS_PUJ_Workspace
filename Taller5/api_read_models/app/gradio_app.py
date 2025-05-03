import gradio as gr
import requests

API_URL = "http://inference_models:8989"  # Servicio FastAPI en docker-compose

def get_models():
    try:
        r = requests.get(f"{API_URL}/models")
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return [f"❌ Error al obtener modelos: {str(e)}"]

def predict(model_name, Soil_Type, Cover_Type, Elevation, Aspect, Slope,
            Horizontal_Distance_To_Hydrology, Vertical_Distance_To_Hydrology,
            Horizontal_Distance_To_Roadways, Hillshade_9am, Hillshade_Noon,
            Hillshade_3pm, Horizontal_Distance_To_Fire_Points, Wilderness_Area):
    
    payload = {
        "Soil_Type": int(Soil_Type),
        "Cover_Type": int(Cover_Type),
        "Elevation": float(Elevation),
        "Aspect": float(Aspect),
        "Slope": float(Slope),
        "Horizontal_Distance_To_Hydrology": float(Horizontal_Distance_To_Hydrology),
        "Vertical_Distance_To_Hydrology": float(Vertical_Distance_To_Hydrology),
        "Horizontal_Distance_To_Roadways": float(Horizontal_Distance_To_Roadways),
        "Hillshade_9am": float(Hillshade_9am),
        "Hillshade_Noon": float(Hillshade_Noon),
        "Hillshade_3pm": float(Hillshade_3pm),
        "Horizontal_Distance_To_Fire_Points": float(Horizontal_Distance_To_Fire_Points),
        "Wilderness_Area": int(Wilderness_Area)
    }

    try:
        r = requests.post(f"{API_URL}/predict/{model_name.split(":")[0]}", json=payload)
        r.raise_for_status()
        return r.json().get("predictions", "Sin predicción")
    except Exception as e:
        return f"❌ Error: {str(e)}"

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
            gr.Number(label="Soil_Type"),
            gr.Number(label="Cover_Type"),
            gr.Number(label="Elevation"),
            gr.Number(label="Aspect"),
            gr.Number(label="Slope"),
            gr.Number(label="Horizontal_Distance_To_Hydrology"),
            gr.Number(label="Vertical_Distance_To_Hydrology"),
            gr.Number(label="Horizontal_Distance_To_Roadways"),
            gr.Number(label="Hillshade_9am"),
            gr.Number(label="Hillshade_Noon"),
            gr.Number(label="Hillshade_3pm"),
            gr.Number(label="Horizontal_Distance_To_Fire_Points"),
            gr.Number(label="Wilderness_Area"),
        ]
    
    output = gr.Textbox(label="📈 Predicción")

    submit_btn = gr.Button("🚀 Predecir")
    submit_btn.click(fn=predict, inputs=input_fields, outputs=output)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)