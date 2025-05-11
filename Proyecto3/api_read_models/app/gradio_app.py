import gradio as gr
import requests

API_URL = "http://inference-models:8989"  # Servicio FastAPI en docker-compose

def get_models():
    try:
        r = requests.get(f"{API_URL}/models")
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return [f"❌ Error al obtener modelos: {str(e)}"]

def predict(model_name, race, gender, age, admission_type_id,
               discharge_disposition_id, admission_source_id, diabetesMed,
               max_glu_serum, A1Cresult, time_in_hospital, num_lab_procedures,
               num_procedures, num_medications, number_outpatient,
               number_emergency, number_inpatient, number_diagnoses 
               ):
    
    payload = {
        "Race": int(race),
        "Gender": int(gender),
        "Age": int(age),
        "admission_type_id": int(admission_type_id),
        "discharge_disposition_id": int(discharge_disposition_id),
        "admission_source_id": int(admission_source_id),
        "diabetesMed": int(diabetesMed),
        "max_glu_serum": int(max_glu_serum),
        "A1Cresult": int(A1Cresult),
        "time_in_hospital": float(time_in_hospital),
        "num_lab_procedures": float(num_lab_procedures),
        "num_procedures": float(num_procedures),
        "num_medications": float(num_medications),
        "number_outpatient": float(number_outpatient),
        "number_emergency": float(number_emergency),
        "number_inpatient": float(number_inpatient),
        "number_diagnoses": int(number_diagnoses)
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
            gr.Number(label= "Race"),
            gr.Number(label="Gender"),
            gr.Number(label="Age"),
            gr.Number(label="admission_type_id"),
            gr.Number(label="discharge_disposition_id"),
            gr.Number(label="admission_source_id"),
            gr.Number(label="diabetesMed"),
            gr.Number(label="max_glu_serum"),
            gr.Number(label="A1Cresult"),
            gr.Number(label="time_in_hospital"),
            gr.Number(label="num_lab_procedures"),
            gr.Number(label="num_procedures"),
            gr.Number(label="num_medications"),
            gr.Number(label="number_outpatient"),
            gr.Number(label="number_emergency"),
            gr.Number(label="number_inpatient"),
            gr.Number(label="number_diagnoses")
        ]
    
    output = gr.Textbox(label="📈 Predicción")

    submit_btn = gr.Button("🚀 Predecir")
    submit_btn.click(fn=predict, inputs=input_fields, outputs=output)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)