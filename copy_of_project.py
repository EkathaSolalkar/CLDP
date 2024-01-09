# -*- coding: utf-8 -*-
"""Copy of project.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1CGxWEVxUyrZ71-Uc1b6rZQ1DUR0lxgiq
"""

# Commented out IPython magic to ensure Python compatibility.
# standard libraries
import numpy as np
import time
import PIL.Image as Image
import matplotlib.pylab as plt
import matplotlib.image as mpimg
# %matplotlib inline
import datetime
from tqdm.keras import TqdmCallback
from skimage import transform
import requests

# tensorflow libraries
import tensorflow as tf
import tensorflow_hub as hub

train_path = '/content/drive/MyDrive/archive'

# define some variables
batch_size = 32
img_height = 256  # reduced from 600 to mitigate the memory issue
img_width = 256   # reduced from 600 to mitigate the memory issue
seed_train_validation = 1
shuffle_value = True
validation_split = 0.4


# load training images
train_ds = tf.keras.utils.image_dataset_from_directory(
  train_path,
  validation_split=validation_split,
  subset="training",
  image_size=(img_height, img_width),
  batch_size=batch_size,
  seed = seed_train_validation,
  shuffle = shuffle_value )

# load validation images
val_ds = tf.keras.utils.image_dataset_from_directory(
    train_path,
    validation_split=validation_split,
    subset="validation",
    image_size=(img_height, img_width),
    batch_size=batch_size,
    seed = seed_train_validation,
    shuffle = shuffle_value )

test_ds_size = int(int(val_ds.__len__()) * 0.5)
test_test_set = val_ds.take(test_ds_size)
test_set = val_ds.skip(test_ds_size)

class_names = train_ds.class_names

# cleaning the class names
class_names = [x.split('_')[1] if '_' in x else x for x in class_names]

# view class names
print("the target classes are: ", *class_names, sep=", ")

# rescaling the images for the model
'''TensorFlow Hub's convention for image models is to expect float inputs in the [0, 1] range'''

normalization_layer = tf.keras.layers.Rescaling(1./255)
train_ds = train_ds.map(lambda x, y: (normalization_layer(x), y)) # Where x—images, y—labels.
val_ds = val_ds.map(lambda x, y: (normalization_layer(x), y)) # Where x—images, y—labels.


'''finish the input pipeline by using buffered prefetching with Dataset.prefetch, so you can yield the data from disk without I/O blocking issues.'''
AUTOTUNE = tf.data.AUTOTUNE
train_ds = train_ds.cache().prefetch(buffer_size=AUTOTUNE)
val_ds = val_ds.cache().prefetch(buffer_size=AUTOTUNE)

"""# Sequential model"""

# get the headless model
'''TensorFlow Hub also distributes models without the top classification layer. These can be used to easily perform transfer learning.'''

# feature vector model
efficientnet_b7_fv = 'https://kaggle.com/models/tensorflow/efficientnet/frameworks/TensorFlow2/variations/b7-feature-vector/versions/1'
feature_extractor_model = efficientnet_b7_fv

# feature extraction layer
'''Create the feature extractor by wrapping the pre-trained model as a Keras layer with hub.KerasLayer. Use the trainable=False argument to freeze the variables, so that the training only modifies the new classifier layer'''
feature_extractor_layer = hub.KerasLayer(
    feature_extractor_model,
    input_shape=(img_width, img_height, 3),
    trainable=False)

# add a classification layer
num_classes = len(class_names)

model = tf.keras.Sequential([
  feature_extractor_layer,
  tf.keras.layers.Dense(num_classes)
])

# model summary
model.summary()

# compile the model
model.compile(
  optimizer=tf.keras.optimizers.Adam(),
  loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
  metrics=['acc'])

# early stopping
early_stopping = tf.keras.callbacks.EarlyStopping(monitor='loss', patience=3)

# Define Epochs
NUM_EPOCHS = 3

history = model.fit(train_ds,
                    validation_data=val_ds,
                    epochs=NUM_EPOCHS,
                    callbacks=[early_stopping, TqdmCallback(verbose=0)],verbose=0)

# view model accuracy
model_acc = '{:.2%}'.format(history.history['acc'][-1])
print(f"\n Model Accuracy Reached: {model_acc}")

# summarize history for accuracy
plt.subplot(2,1,1)
plt.plot(history.history['acc'])
plt.plot(history.history['val_acc'])
plt.title('model accuracy')
plt.ylabel('accuracy')
plt.xlabel('epoch')
plt.legend(['train', 'test'], loc='upper left')
plt.show()
# summarize history for loss
plt.subplot(2,1,2)
plt.plot(history.history['loss'])
plt.plot(history.history['val_loss'])
plt.title('model loss')
plt.ylabel('loss')
plt.xlabel('epoch')
plt.legend(['train', 'test'], loc='upper left')
plt.show()

"""# **VGG16**"""

pip install livelossplot

from keras.layers import Dense, Flatten
from keras.models import Sequential, Model
from keras.callbacks import ModelCheckpoint
from keras import regularizers
from livelossplot import PlotLossesKeras
from tensorflow.keras.applications.vgg16 import VGG16

vgg16 = VGG16(include_top=False, weights='imagenet', input_shape=(256,256,3))
output = vgg16.layers[-1].output
output = Flatten()(output)
vgg16 = Model(vgg16.input, output)
for layer in vgg16.layers:
    layer.trainable = False
vgg16.summary()

model_1 = Sequential()

model_1.add(vgg16)
model_1.add(Dense(128,activation='relu', input_dim=(128,128,3), kernel_regularizer=regularizers.L2(0.05)))
model_1.add(Dense(64,activation='relu', kernel_regularizer=regularizers.L2(0.05)))
model_1.add(Dense(1,activation='softmax'))

model_1.compile(optimizer='adam',loss='categorical_crossentropy',metrics=['accuracy','Recall','Precision','AUC'])

filepath = "/content/drive/MyDrive/Models/vgg16-model-t5.h5"

callbacks = [ModelCheckpoint(filepath=filepath, monitor="val_accuracy", mode='max', save_best_only=True),
            PlotLossesKeras()]

h = model_1.fit(train_ds,
                epochs=3,
                validation_data=val_ds,
                callbacks=callbacks
                )

model_1.evaluate(test_test_set)

"""# **Restnet model**"""

from tensorflow.keras.preprocessing import image_dataset_from_directory
RANDOM_SEED = 42

path_ = "/content/drive/MyDrive/archive"

train_batch = 64
test_batch = 64
train_set= image_dataset_from_directory(path_,
                                labels='inferred',
                                label_mode='categorical',
                                batch_size=train_batch,
                                seed=RANDOM_SEED,
                                shuffle=True,
                                validation_split=0.2,
                                subset='training')

val_set =  image_dataset_from_directory(path_,
                                labels='inferred',
                                label_mode='categorical',
                                batch_size=test_batch,
                                seed=RANDOM_SEED,
                                shuffle=True,
                                validation_split=0.2,
                                subset='validation')

test_ds_size = int(34 * 0.5)
test_test_set = val_set.take(test_ds_size)
test_set = val_set.skip(test_ds_size)

from keras.layers import Dense, Flatten
from keras.models import Sequential, Model
from keras.callbacks import ModelCheckpoint
from keras import regularizers
from livelossplot import PlotLossesKeras
from tensorflow.keras.applications.resnet50 import ResNet50

restnet = ResNet50(include_top=False, weights='imagenet', input_shape=(256,256,3))
output = restnet.layers[-1].output
output = Flatten()(output)
restnet = Model(restnet.input, output)
for layer in restnet.layers:
    layer.trainable = False
restnet.summary()

model_1 = Sequential()

model_1.add(restnet)
model_1.add(Dense(128,activation='relu', input_dim=(256,256,3), kernel_regularizer=regularizers.L2(0.001)))
model_1.add(Dense(64,activation='relu', kernel_regularizer=regularizers.L2(0.001)))
model_1.add(Dense(5,activation='softmax'))

model_1.compile(optimizer='adam',loss='categorical_crossentropy',metrics=['accuracy','Recall','Precision','AUC'])

filepath = "/content/drive/MyDrive/Models/resnet-model-t3.h5"

callbacks = [ModelCheckpoint(filepath=filepath, monitor="val_accuracy", mode='max', save_best_only=True),
            PlotLossesKeras()]

h = model_1.fit(train_ds,
                epochs=3,
                validation_data=val_ds,
                callbacks=callbacks
                )

model_1.evaluate(test_test_set)