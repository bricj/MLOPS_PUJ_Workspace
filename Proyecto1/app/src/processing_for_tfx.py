import tensorflow as tf
import tensorflow_transform as tft

#variables numericas
quantitative_variables = ['Elevation', 'Aspect', 'Slope', 'Horizontal_Distance_To_Hydrology',
       'Vertical_Distance_To_Hydrology', 'Horizontal_Distance_To_Roadways',
       'Hillshade_9am', 'Hillshade_Noon', 'Hillshade_3pm',
       'Horizontal_Distance_To_Fire_Points']

#variables categoricas
categorical_variables = ['Wilderness_Area', 'Soil_Type']

#funcion para el artefacto Transform
def preprocessing_fn(inputs):
    outputs = {}

    # Normalizar variables numericas
    for col in quantitative_variables:
        outputs[col] = tft.scale_to_z_score(inputs[col])

    # realizar one hot encoding a variables categoricas
    for col in categorical_variables:
        outputs[col] = tft.compute_and_apply_vocabulary(inputs[col])

    return outputs
