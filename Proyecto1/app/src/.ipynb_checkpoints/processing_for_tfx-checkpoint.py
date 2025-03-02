import tensorflow as tf
import tensorflow_transform as tft

quantitative_variables = ['Elevation', 'Aspect', 'Slope', 'Horizontal_Distance_To_Hydrology',
       'Vertical_Distance_To_Hydrology', 'Horizontal_Distance_To_Roadways',
       'Hillshade_9am', 'Hillshade_Noon', 'Hillshade_3pm',
       'Horizontal_Distance_To_Fire_Points']

categorical_variables = ['Wilderness_Area', 'Soil_Type']

def preprocessing_fn(inputs):
    """Preprocess input features using TF Transform."""
    outputs = {}

    # Normalize numerical features
    for col in quantitative_variables:
        outputs[col] = tft.scale_to_z_score(inputs[col])

    # Convert categorical feature into one-hot encoding
    for col in categorical_variables:
        outputs[col] = tft.compute_and_apply_vocabulary(inputs[col])

    return outputs