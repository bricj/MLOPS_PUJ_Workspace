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

def get_annotations():
    try:
        r = requests.get(f"{API_URL}/annotations")
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return [f"❌ Error al obtener las anotaciones: {str(e)}"]

def predict(model_name,acre_lot,house_size,rate_bath_bed,room_configuration_minimal_rooms,room_configuration_compact_rooms,room_configuration_standard_rooms,room_configuration_spacious_rooms,room_configuration_luxury_rooms,region_west):
    
    payload = {
        "acre_lot":float(acre_lot),
        "house_size":float(house_size),
        "rate_bath_bed":float(rate_bath_bed),
        "room_configuration_minimal_rooms":float(room_configuration_minimal_rooms),
        "room_configuration_compact_rooms":float(room_configuration_compact_rooms),
        "room_configuration_standard_rooms":float(room_configuration_standard_rooms),
        "room_configuration_spacious_rooms":float(room_configuration_spacious_rooms),
        "room_configuration_luxury_rooms":float(room_configuration_luxury_rooms),
        "region_west":float(region_west)
    }

    try:
        mod = model_name.split(":")[0]
        r = requests.post(f"{API_URL}/predict/{mod}", json=payload)
        r.raise_for_status()
        return r.json().get("predictions", "Sin predicción")
    except Exception as e:
        return f"❌ Error para {model_name}: {str(e)}"

def update_model_choices():
    return gr.update(choices=get_models())

def update_annotations():
    return get_annotations()

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
            gr.Number(label="acre lot"),
            gr.Number(label="house size"),
            gr.Number(label="rate bath bed"),
            gr.Number(label="room configuration minimal rooms"),
            gr.Number(label="room configuration compact rooms"),
            gr.Number(label="room configuration standard rooms"),
            gr.Number(label="room configuration spacious rooms"),
            gr.Number(label="room configuration luxury rooms"),
            gr.Number(label="region west")
        ]
    
    output = gr.Textbox(label="📈 Predicción")

    submit_btn = gr.Button("🚀 Predecir")
    submit_btn.click(fn=predict, inputs=input_fields, outputs=output)

    with gr.Row():
        model_annotation = gr.Textbox(label="✏️ Anotaciones", lines=10)
        reload_button_ann = gr.Button("🔄 Recargar anotaciones")
        reload_button_ann.click(fn=update_annotations, outputs=model_annotation)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)