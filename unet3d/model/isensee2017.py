from functools import partial

from tensorflow.keras.layers import Input, LeakyReLU, Add, UpSampling3D, Activation, SpatialDropout3D, Conv3D
from tensorflow.keras import Model
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.losses import categorical_crossentropy
import tensorflow.keras.backend as K
import re
from .unet import create_convolution_block, concatenate
from ..metrics import weighted_dice_coefficient_loss, dice_coef, jaccard_distance_loss, dice_coef_loss
from ..generalized_loss import generalized_dice_loss, dice
#
create_convolution_block = partial(create_convolution_block, activation=LeakyReLU, instance_normalization=True)

def isensee2017_model(input_shape=(2, 200, 200, 200), n_base_filters=16, depth=5, dropout_rate=0.3,
                      n_segmentation_levels=3, n_labels=1, optimizer=Adam, initial_learning_rate=5e-4,
                      loss_function="weighted_dice_coefficient_loss", activation_name="sigmoid", shortcut=True, compile = True):
                          
    """
    This function builds a model proposed by Isensee et al. for the BRATS 2017 competition:
    https://www.cbica.upenn.edu/sbia/Spyridon.Bakas/MICCAI_BraTS/MICCAI_BraTS_2017_proceedings_shortPapers.pdf

    This network is highly similar to the model proposed by Kayalibay et al. "CNN-based Segmentation of Medical
    Imaging Data", 2017: https://arxiv.org/pdf/1701.03056.pdf

    :param input_shape:
    :param n_base_filters:
    :param depth:
    :param dropout_rate:
    :param n_segmentation_levels:
    :param n_labels:
    :param optimizer:
    :param initial_learning_rate:
    :param loss_function:
    :param activation_name:
    :return:
    """

    loss_function_d = {
        "weighted_dice_coefficient_loss": weighted_dice_coefficient_loss,
        "generalized_dice_loss": generalized_dice_loss,
        "jaccard_distance_loss": jaccard_distance_loss,
        "categorical_crossentropy": categorical_crossentropy,
        "dice_coefficient_loss": dice_coef_loss
    }

    loss_function = loss_function_d[loss_function]
    output = []
    inputs = Input(input_shape)

    current_layer = inputs
    level_output_layers = list()
    level_filters = list()
    for level_number in range(depth):
        n_level_filters = (2**level_number) * n_base_filters
        level_filters.append(n_level_filters)

        if current_layer is inputs:
            in_conv = create_convolution_block(current_layer, n_level_filters)
        else:
            in_conv = create_convolution_block(current_layer, n_level_filters, strides=(2, 2, 2))

        context_output_layer, context_module_name = create_context_module(in_conv, n_level_filters, dropout_rate=dropout_rate)

        output += [re.findall("[^\/]*",context_module_name)[0]]

        summation_layer = Add()([in_conv, context_output_layer])
        level_output_layers.append(summation_layer)
        current_layer = summation_layer

    segmentation_layers = list()
    for level_number in range(depth - 2, -1, -1):
        up_sampling, up_sampling_name = create_up_sampling_module(current_layer, level_filters[level_number])
        output += [re.findall("[^\/]*", up_sampling_name)[0]]
        if shortcut:
            concatenation_layer = concatenate([level_output_layers[level_number], up_sampling], axis=1)
            localization_output = create_localization_module(concatenation_layer, level_filters[level_number])
        else:
            localization_output = create_localization_module(up_sampling, level_filters[level_number])
        current_layer = localization_output
        if level_number < n_segmentation_levels:
            segmentation_layers.insert(0, Conv3D(n_labels, (1, 1, 1))(current_layer))

    output_layer = None
    for level_number in reversed(range(n_segmentation_levels)):
        segmentation_layer = segmentation_layers[level_number]
        if output_layer is None:
            output_layer = segmentation_layer
        else:
            output_layer = Add()([output_layer, segmentation_layer])

        if level_number > 0:
            output_layer = UpSampling3D(size=(2, 2, 2))(output_layer)

    activation_block = Activation(activation_name)(output_layer)

    model = Model(inputs=inputs, outputs=activation_block)
    if compile:
        model.compile(optimizer=optimizer(lr=initial_learning_rate), loss=loss_function, metrics=[dice_coef])
    return model, output


def create_localization_module(input_layer, n_filters):
    convolution1 = create_convolution_block(input_layer, n_filters)
    convolution2 = create_convolution_block(convolution1, n_filters, kernel=(1, 1, 1))
    return convolution2


def create_up_sampling_module(input_layer, n_filters, size=(2, 2, 2)):
    up_sample = UpSampling3D(size=size)(input_layer)
    convolution = create_convolution_block(up_sample, n_filters)
    return convolution, convolution.name


def create_context_module(input_layer, n_level_filters, dropout_rate=0.3, data_format="channels_first"):
    convolution1 = create_convolution_block(input_layer=input_layer, n_filters=n_level_filters)
    dropout = SpatialDropout3D(rate=dropout_rate, data_format=data_format)(convolution1)
    convolution2 = create_convolution_block(input_layer=dropout, n_filters=n_level_filters)
    return convolution2, convolution2.name



