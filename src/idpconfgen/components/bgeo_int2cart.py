'''Using the machine learning Int2Cart algorithm for providing bond geometries'''

from modelling.utils.predict import predict
from modelling.models.builder import BackboneBuilder
import yaml
import torch

class BGEO_Int2Cart:
    def __init__(self, model_config="int2cart/int2cart.yml", model_addr="int2cart/model.tar") -> None:
        settings = yaml.safe_load(open(model_config, "r"))
        builder = BackboneBuilder(settings)
        model_state = torch.load(model_addr)['model_state_dict']
        builder.load_predictor_weights(model_state)
        self.builder = builder

    def get_internal_coords(self, sequence, torsions):
        predictions = predict(self.builder, sequence, torsions, build=False)
        d1 = predictions['d1'][0, -1]
        d2 = predictions['d2'][0, -1]
        d3 = predictions['d3'][0, -1]
        theta1 = predictions['theta1'][0, -1]
        theta2 = predictions['theta2'][0, -1]
        theta3 = predictions['theta3'][0, -1]
        return (d1, d2, d3, theta1, theta2, theta3)