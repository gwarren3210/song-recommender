import torch
from transformers import ClapModel, ClapProcessor

def load_model(model_name="laion/clap-htsat-unfused"):
    """
    Loads the CLAP model and processor from HuggingFace.
    
    Args:
        model_name (str): The name of the model to load.
        
    Returns:
        model (ClapModel): The loaded CLAP model.
        processor (ClapProcessor): The loaded processor.
    """
    print(f"Loading CLAP model: {model_name}...")
    try:
        model = ClapModel.from_pretrained(model_name)
        processor = ClapProcessor.from_pretrained(model_name)
        
        if torch.cuda.is_available():
            model = model.to("cuda")
            print("Model moved to CUDA.")
        elif torch.backends.mps.is_available():
             model = model.to("mps")
             print("Model moved to MPS.")
        else:
            print("Using CPU.")
            
        return model, processor
    except Exception as e:
        print(f"Error loading model: {e}")
        raise e
