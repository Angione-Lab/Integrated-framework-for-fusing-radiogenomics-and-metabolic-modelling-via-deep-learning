# -*- coding: utf-8 -*-
"""
Created on Thu Oct 28 15:45:44 2021

@author: Noushin
"""

import os
import zipfile
import numpy as np
import tensorflow as tf

from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.callbacks import ModelCheckpoint
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Activation, Flatten, BatchNormalization, Dropout
from tensorflow.keras.metrics import Metric
from sklearn.model_selection import train_test_split
# from sksurv.metrics import concordance_index_censored
import numpy as np
import pandas as pd
import warnings
from typing import Optional

warnings.filterwarnings('ignore')
warnings.filterwarnings('ignore', category=DeprecationWarning)
tf.config.run_functions_eagerly(True)

# %%
# Loading data

# import seaborn as sns
main_path = r'D:\Mojtaba\Test\noushin'

OV_RNa_seq = pd.read_csv(os.path.join(main_path, 'TCGA-noiso-ENSG.csv'), header=None)

OV_RNa_seq = OV_RNa_seq.T
header = OV_RNa_seq.iloc[0]
OV_RNa_seq = OV_RNa_seq[1:]
OV_RNa_seq = OV_RNa_seq.rename(columns=header)
OV_RNa_seq['EnsemblgeneID'] = OV_RNa_seq['EnsemblgeneID'].str[:12]

# Pan_RNa_seq_T.dropna(inplace =  True)
OV_RNa_seq.dropna(inplace=True)

Survival_Data = pd.read_excel(os.path.join(main_path, 'survival.xlsx'), sheet_name='TCGA-CDR', usecols="A,B,Y, Z")
Survival_Data.dropna(inplace=True)

Survival_Data_pan = Survival_Data.loc[Survival_Data['type'] != "OV"]
Survival_Data_ov = Survival_Data.loc[Survival_Data['type'] == "OV"]

OV_RNa_seq_sur = pd.merge(OV_RNa_seq, Survival_Data_ov, on='EnsemblgeneID')
print(OV_RNa_seq_sur.shape)
OV_RNa_seq_sur.head()

X = OV_RNa_seq_sur.loc[:, 'ENSG00000000003':'ENSG00000288642'].values
X = np.asarray(X).astype('float32')

y1 = OV_RNa_seq_sur.loc[:, 'OS'].values
y2 = OV_RNa_seq_sur.loc[:, 'OS.time'].values

y_ov = np.array([y1, y2]).T

# get list of OV samples without and  images
img_list = pd.read_csv(os.path.join(main_path, 'image_ids.csv'))

# OV RNA seq and survival with common with images
OV_RNa_seq_image = OV_RNa_seq_sur[OV_RNa_seq_sur['EnsemblgeneID'].isin(img_list['EnsemblgeneID'])].loc[:,
                   'ENSG00000000003':'ENSG00000288642'].values
OV_RNa_seq_image = np.asarray(OV_RNa_seq_image).astype('float32')
ov_survival_img = OV_RNa_seq_sur[OV_RNa_seq_sur['EnsemblgeneID'].isin(img_list['EnsemblgeneID'])][
    ['OS', 'OS.time']].values

# from sklearn.preprocessing import minmax_scale
# train_scaled = minmax_scale(X, axis = 0)
# X_train= OV_RNa_seq_without_image
y_train = ov_survival_img[:30]
# %%
import nibabel as nib

from scipy import ndimage


def read_nifti_file(filepath):
    """Read and load volume"""
    # Read file
    scan = nib.load(filepath)
    # Get raw data
    scan = scan.get_fdata()
    return scan


def normalize(volume):
    """Normalize the volume"""
    min = -1024
    max = 400
    volume[volume < min] = min
    volume[volume > max] = max
    volume = (volume - min) / (max - min)
    volume = volume.astype("float32")
    return volume


def resize_volume(img):
    """Resize across z-axis"""
    # Set the desired depth
    desired_depth = 64
    desired_width = 128
    desired_height = 128
    # Get current depth
    current_depth = img.shape[-1]
    current_width = img.shape[0]
    current_height = img.shape[1]
    # Compute depth factor
    depth = current_depth / desired_depth
    width = current_width / desired_width
    height = current_height / desired_height
    depth_factor = 1 / depth
    width_factor = 1 / width
    height_factor = 1 / height
    # Rotate
    img = ndimage.rotate(img, 90, reshape=False)
    # Resize across z-axis
    img = ndimage.zoom(img, (width_factor, height_factor, depth_factor), order=1)
    return img


def process_scan(path):
    """Read and resize volume"""
    # Read scan
    volume = read_nifti_file(path)
    # Normalize
    volume = normalize(volume)
    # Resize width, height and depth
    # volume = resize_volume(volume)
    return volume


# %%
# Folder "CT-0" consist of CT scans having normal lung tissue,
# no CT-signs of viral pneumonia.
# normal_scan_paths = [
#     os.path.join(os.getcwd(), "MosMedData/CT-0", x)
#     for x in os.listdir("MosMedData/CT-0")
# ]
# Folder "CT-23" consist of CT scans having several ground-glass opacifications,
# involvement of lung parenchyma.

abnormal_scan_paths = [
    os.path.join(main_path, "CT_patch", x)
    for x in os.listdir(os.path.join(main_path, "CT_patch"))
]

# print("CT scans with normal lung tissue: " + str(len(normal_scan_paths)))
print("CT scans with abnormal lung tissue: " + str(len(abnormal_scan_paths)))
# %%
# Read and process the scans.
# Each scan is resized across height, width, and depth and rescaled.
abnormal_scans = np.array([process_scan(path) for path in abnormal_scan_paths])
# normal_scans = np.array([process_scan(path) for path in normal_scan_paths])

# For the CT scans having presence of viral pneumonia
# assign 1, for the normal ones assign 0.
# abnormal_labels = np.array([1 for _ in range(len(abnormal_scans))])
abnormal_labels = np.zeros([len(abnormal_scan_paths), 2])
for i in range(len(abnormal_scan_paths)):
    str1 = str.split(abnormal_scan_paths[i], '\\')[-1]
    # str2 = str.split(str1, '.')[0]

    index = np.where(Survival_Data.values[:, 0] == str.split(str1, '.')[0])[0]
    abnormal_labels[i, :] = Survival_Data.values[index, 2:4]

# normal_labels = np.array([0 for _ in range(len(normal_scans))])

# Split data in the ratio 70-30 for training and validation.
# x_train = np.concatenate((abnormal_scans[:70], normal_scans[:70]), axis=0)
# y_train = np.concatenate((abnormal_labels[:70], normal_labels[:70]), axis=0)
# x_val = np.concatenate((abnormal_scans[70:], normal_scans[70:]), axis=0)
# y_val = np.concatenate((abnormal_labels[70:], normal_labels[70:]), axis=0)
x_train = abnormal_scans
y_train = abnormal_labels
print(
    "Number of samples in train are %d." % (x_train.shape[0])
)
# %%
import random

from scipy import ndimage


@tf.function
def rotate(volume):
    """Rotate the volume by a few degrees"""

    def scipy_rotate(volume):
        # define some rotation angles
        angles = [-20, -10, -5, 5, 10, 20]
        # pick angles at random
        angle = random.choice(angles)
        # rotate volume
        volume = ndimage.rotate(volume, angle, reshape=False)
        volume[volume < 0] = 0
        volume[volume > 1] = 1
        return volume

    augmented_volume = tf.numpy_function(scipy_rotate, [volume], tf.float32)
    return augmented_volume


def train_preprocessing(volume, label):
    """Process training data by rotating and adding a channel."""
    # Rotate volume
    volume = rotate(volume)
    volume = tf.expand_dims(volume, axis=3)
    return volume, label


def validation_preprocessing(volume, label):
    """Process validation data by only adding a channel."""
    volume = tf.expand_dims(volume, axis=3)
    return volume, label


# %%
# Define data loaders.
train_loader = tf.data.Dataset.from_tensor_slices((x_train, y_train))
# validation_loader = tf.data.Dataset.from_tensor_slices((x_val, y_val))

batch_size = 2
# Augment the on the fly during training.
train_dataset = (
    train_loader.shuffle(len(x_train))
        .batch(batch_size)
        .prefetch(2)
)


# # Only rescale.
# validation_dataset = (
#     validation_loader.shuffle(len(x_val))
#     .map(validation_preprocessing)
#     .batch(batch_size)
#     .prefetch(2)
# )
# %%

def R_set(x):
    n_sample = x.shape[0]
    matrix_ones = tf.ones([n_sample, n_sample], tf.int32)
    indicator_matrix = tf.compat.v1.matrix_band_part(matrix_ones, -1, 0)

    return (indicator_matrix)


def safe_normalize(x):
    """Normalize risk scores to avoid exp underflowing.

    Note that only risk scores relative to each other matter.
    If minimum risk score is negative, we shift scores so minimum
    is at zero.
    """
    x_min = tf.reduce_min(x, axis=0)
    c = tf.zeros_like(x_min)
    norm = tf.where(x_min < 0, -x_min, c)
    return x + norm


def logsumexp_masked(risk_scores,
                     mask,
                     axis,
                     keepdims: Optional[bool] = None):
    """Compute logsumexp across `axis` for entries where `mask` is true."""
    risk_scores.shape.assert_same_rank(mask.shape)

    with tf.name_scope("logsumexp_masked"):
        mask_f = tf.cast(mask, risk_scores.dtype)
        risk_scores_masked = tf.math.multiply(risk_scores, mask_f)
        # for numerical stability, substract the maximum value
        # before taking the exponential
        amax = tf.reduce_max(risk_scores_masked, axis=axis, keepdims=True)
        risk_scores_shift = risk_scores_masked - amax

        exp_masked = tf.math.multiply(tf.exp(risk_scores_shift), mask_f)
        exp_sum = tf.reduce_sum(exp_masked, axis=axis, keepdims=True)
        output = amax + tf.math.log(exp_sum)
        if not keepdims:
            output = tf.squeeze(output, axis=axis)
    return output


class CoxPHLoss(tf.keras.losses.Loss):
    """Negative partial log-likelihood of Cox's proportional hazards model."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def call(self, y_true, y_pred):
        event = y_true[:, 0]
        time = y_true[:, 1]
        predictions = y_pred

        # sort data
        time, idx = tf.nn.top_k(time, k=len(time))
        event = tf.gather(event, indices=idx, axis=0)
        predictions = tf.gather(predictions, indices=idx, axis=0)
        riskset = R_set(time)

        event = tf.cast(event, predictions.dtype)
        predictions = safe_normalize(predictions)

        pred_t = tf.transpose(predictions)
        # compute log of sum over risk set for each row
        rr = logsumexp_masked(pred_t, riskset, axis=1, keepdims=True)
        assert rr.shape.as_list() == predictions.shape.as_list()

        losses = tf.math.multiply(event, rr - predictions)

        return losses


class CindexMetric(Metric):

    def reset_states(self):
        """Clear the buffer of collected values."""
        self._data = {
            "label_time": [],
            "label_event": [],
            "prediction": []
        }

    def update_state(self, y_time, y_event, y_pred):
        self._data["label_time"].append(tf.squeeze(y_time).numpy())
        self._data["label_event"].append(tf.squeeze(y_event).numpy())
        self._data["prediction"].append(tf.squeeze(y_pred).numpy())

    def result(self):
        data = {}

        for k, v in self._data.items():
            data[k] = np.concatenate(v)

        results = concordance_index_censored(
            data["label_event"] == 1,
            data["label_time"],
            data["prediction"])

        return results[0]


class MlpCoxModel(tf.keras.Model):

    def __init__(self, cox_model, training=True, **kwargs):
        super(MlpCoxModel, self).__init__(**kwargs)

        self.cox_loss_tracker = tf.keras.metrics.Mean(name="cox_loss")
        self.cox_model = cox_model

        self.loss_fn = CoxPHLoss()
        self.val_cindex_metric = CindexMetric()

    @property
    def metrics(self):
        return [
            self.val_cindex_metric
        ]

    def train_step(self, data):
        x, y = data

        y_event = y[:, 0]
        y_time = y[:, 1]

        with tf.GradientTape() as tape:
            y_pred = self.cox_model(x, training=True)
            loss = self.loss_fn(y_true=y, y_pred=y_pred)

        # Compute gradients
        trainable_vars = self.trainable_variables
        gradients = tape.gradient(loss, self.trainable_weights)
        # Update weights
        self.optimizer.apply_gradients(zip(gradients, self.trainable_weights))
        self.cox_loss_tracker.update_state(loss)
        self.val_cindex_metric.update_state(y_time, y_event, y_pred)
        # Update metrics (includes the metric that tracks the loss)
        self.compiled_metrics.update_state(y, y_pred)

        return {
            "cox_loss": self.cox_loss_tracker.result(),
            "c_index": self.val_cindex_metric.result()
        }

    # validation metric; validation c-index
    def test_step(self, data):
        x, y = data
        y_event = y[:, 0]
        y_time = y[:, 1]
        y_pred = self.cox_model(x, training=False)
        self.val_cindex_metric.update_state(y_time, y_event, y_pred)
        return {
            "c_index": self.val_cindex_metric.result()
        }

    # evaluation metric; evaluation c-index
    def evaluate_step(self, data):
        x, y = data
        y_event = y[:, 0]
        y_time = y[:, 1]
        y_pred = self.cox_model(x, training=False)
        self.val_cindex_metric.update_state(y_time, y_event, y_pred)
        return {
            "c_index": self.val_cindex_metric.result()
        }


def R_set(x):
    n_sample = x.shape[0]
    matrix_ones = tf.ones([n_sample, n_sample], tf.int32)
    indicator_matrix = tf.compat.v1.matrix_band_part(matrix_ones, -1, 0)

    return (indicator_matrix)


def safe_normalize(x):
    """Normalize risk scores to avoid exp underflowing.

    Note that only risk scores relative to each other matter.
    If minimum risk score is negative, we shift scores so minimum
    is at zero.
    """
    x_min = tf.reduce_min(x, axis=0)
    c = tf.zeros_like(x_min)
    norm = tf.where(x_min < 0, -x_min, c)
    return x + norm


def logsumexp_masked(risk_scores,
                     mask,
                     axis,
                     keepdims: Optional[bool] = None):
    """Compute logsumexp across `axis` for entries where `mask` is true."""
    risk_scores.shape.assert_same_rank(mask.shape)

    with tf.name_scope("logsumexp_masked"):
        mask_f = tf.cast(mask, risk_scores.dtype)
        risk_scores_masked = tf.math.multiply(risk_scores, mask_f)
        # for numerical stability, substract the maximum value
        # before taking the exponential
        amax = tf.reduce_max(risk_scores_masked, axis=axis, keepdims=True)
        risk_scores_shift = risk_scores_masked - amax

        exp_masked = tf.math.multiply(tf.exp(risk_scores_shift), mask_f)
        exp_sum = tf.reduce_sum(exp_masked, axis=axis, keepdims=True)
        output = amax + tf.math.log(exp_sum)
        if not keepdims:
            output = tf.squeeze(output, axis=axis)
    return output


class CoxPHLoss(tf.keras.losses.Loss):
    """Negative partial log-likelihood of Cox's proportional hazards model."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def call(self, y_true, y_pred):
        event = y_true[:, 0]
        time = y_true[:, 1]
        predictions = y_pred

        # sort data
        time, idx = tf.nn.top_k(time, k=len(time))
        event = tf.gather(event, indices=idx, axis=0)
        predictions = tf.gather(predictions, indices=idx, axis=0)
        riskset = R_set(time)

        event = tf.cast(event, predictions.dtype)
        predictions = safe_normalize(predictions)

        pred_t = tf.transpose(predictions)
        # compute log of sum over risk set for each row
        rr = logsumexp_masked(pred_t, riskset, axis=1, keepdims=True)
        assert rr.shape.as_list() == predictions.shape.as_list()

        losses = tf.math.multiply(event, rr - predictions)

        return losses


class CindexMetric(Metric):

    def reset_states(self):
        """Clear the buffer of collected values."""
        self._data = {
            "label_time": [],
            "label_event": [],
            "prediction": []
        }

    def update_state(self, y_time, y_event, y_pred):
        self._data["label_time"].append(tf.squeeze(y_time).numpy())
        self._data["label_event"].append(tf.squeeze(y_event).numpy())
        self._data["prediction"].append(tf.squeeze(y_pred).numpy())

    def result(self):
        data = {}

        for k, v in self._data.items():
            data[k] = np.concatenate(v)

        results = concordance_index_censored(
            data["label_event"] == 1,
            data["label_time"],
            data["prediction"])

        return results[0]


class MlpCoxModel(tf.keras.Model):

    def __init__(self, cox_model, training=True, **kwargs):
        super(MlpCoxModel, self).__init__(**kwargs)

        self.cox_loss_tracker = tf.keras.metrics.Mean(name="cox_loss")
        self.cox_model = cox_model

        self.loss_fn = CoxPHLoss()
        self.val_cindex_metric = CindexMetric()

    @property
    def metrics(self):
        return [
            self.val_cindex_metric
        ]

    def train_step(self, data):
        x, y = data

        y_event = y[:, 0]
        y_time = y[:, 1]

        with tf.GradientTape() as tape:
            y_pred = self.cox_model(x, training=True)
            loss = self.loss_fn(y_true=y, y_pred=y_pred)

        # Compute gradients
        trainable_vars = self.trainable_variables
        gradients = tape.gradient(loss, self.trainable_weights)
        # Update weights
        self.optimizer.apply_gradients(zip(gradients, self.trainable_weights))
        self.cox_loss_tracker.update_state(loss)
        self.val_cindex_metric.update_state(y_time, y_event, y_pred)
        # Update metrics (includes the metric that tracks the loss)
        self.compiled_metrics.update_state(y, y_pred)

        return {
            "cox_loss": self.cox_loss_tracker.result(),
            "c_index": self.val_cindex_metric.result()
        }

    # validation metric; validation c-index
    def test_step(self, data):
        x, y = data
        y_event = y[:, 0]
        y_time = y[:, 1]
        y_pred = self.cox_model(x, training=False)
        self.val_cindex_metric.update_state(y_time, y_event, y_pred)
        return {
            "c_index": self.val_cindex_metric.result()
        }

    # evaluation metric; evaluation c-index
    def evaluate_step(self, data):
        x, y = data
        y_event = y[:, 0]
        y_time = y[:, 1]
        y_pred = self.cox_model(x, training=False)
        self.val_cindex_metric.update_state(y_time, y_event, y_pred)
        return {
            "c_index": self.val_cindex_metric.result()
        }


# %%
def get_model(width=256, height=256, depth=20):
    """Build a 3D convolutional neural network model."""

    inputs = keras.Input((width, height, depth, 1))

    x = layers.Conv3D(filters=64, kernel_size=3, activation="relu", padding='same')(inputs)
    x = layers.MaxPool3D(pool_size=2)(x)
    x = layers.BatchNormalization()(x)

    x = layers.Conv3D(filters=64, kernel_size=3, activation="relu", padding='same')(x)
    x = layers.MaxPool3D(pool_size=2)(x)
    x = layers.BatchNormalization()(x)

    x = layers.Conv3D(filters=128, kernel_size=3, activation="relu", padding='same')(x)
    x = layers.MaxPool3D(pool_size=2)(x)
    x = layers.BatchNormalization()(x)

    x = layers.Conv3D(filters=256, kernel_size=3, activation="relu", padding='same')(x)
    x = layers.MaxPool3D(pool_size=2)(x)
    x = layers.BatchNormalization()(x)

    x = layers.GlobalAveragePooling3D()(x)
    x = layers.Dense(units=512, activation="relu")(x)
    x = layers.Dropout(0.3)(x)

    outputs = layers.Dense(units=1, activation="linear")(x)

    # Define the model.
    model = keras.Model(inputs, outputs, name="3dcnn")
    return model


# Build model.

model = get_model(width=256, height=256, depth=20)
model.summary()

mlp_cox_model = MlpCoxModel(model)
adam = tf.keras.optimizers.Adam(learning_rate=0.000001, decay=0.001)
mlp_cox_model.compile(optimizer=adam)

model = get_model(width=256, height=256, depth=20)
model.summary()
# %%
mlp_cox_model.fit(x_train, y_train, epochs=2, batch_size=4, validation_split=0.1)
# %%