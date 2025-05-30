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

def predict(model_name,bed,bath,acre_lot,street,zip_code,house_size,city,state,brokered_by,prev_sold_date):
    
    payload = {
        "bed": float(bed),
        "bath": float(bath),
        "acre_lot": float(acre_lot),
        "street": str(street),
        "zip_code": str(zip_code),
        "house_size": float(house_size),
        "city": str(city),
        "state": str(state),
        "brokered_by": str(brokered_by),
        "prev_sold_date": str(prev_sold_date)
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
            gr.Number(label="bed"),
            gr.Number(label="bath"),
            gr.Number(label="acre_lot"),
            gr.Textbox(label="street"),
            gr.Textbox(label="zip_code"),
            gr.Number(label="house_size"),
            gr.Textbox(label="city"),
            gr.Textbox(label="state"),
            gr.Textbox(label="brokered_by"),
            gr.Textbox(label="prev_sold_date")
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