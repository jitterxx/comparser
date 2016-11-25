#!/usr/bin/python3 -t
# coding: utf8


import tensorflow as tf
import numpy as np
from tensorflow.contrib import learn
from helpers import data_helpers_conparser
import os



class TextCNN(object):
    """
    A CNN for text classification.
    Uses an embedding layer, followed by a convolutional, max-pooling and softmax layer.
    """
    def __init__(self, sequence_length, num_classes, vocab_size,
                 embedding_size, filter_sizes, num_filters, l2_reg_lambda=0.0):

        # Placeholders for input, output and dropout
        self.input_x = tf.placeholder(tf.int32, [None, sequence_length], name="input_x")
        self.input_y = tf.placeholder(tf.float32, [None, num_classes], name="input_y")
        self.dropout_keep_prob = tf.placeholder(tf.float32, name="dropout_keep_prob")

        # Keeping track of l2 regularization loss (optional)
        l2_loss = tf.constant(0.0)

        # Embedding layer
        with tf.device('/cpu:0'), tf.name_scope("embedding"):
            self.W = tf.Variable(
                tf.random_uniform([vocab_size, embedding_size], -1.0, 1.0),
                trainable=False,
                name="W")
            self.embedded_chars = tf.nn.embedding_lookup(self.W, self.input_x)
            self.embedded_chars_expanded = tf.expand_dims(self.embedded_chars, -1)


        # Create a convolution + maxpool layer for each filter size
        pooled_outputs = []
        for i, filter_size in enumerate(filter_sizes):
            with tf.name_scope("conv-maxpool-%s" % filter_size):
                # Convolution Layer
                filter_shape = [filter_size, embedding_size, 1, num_filters]
                W = tf.Variable(tf.truncated_normal(filter_shape, stddev=0.1), name="W")
                b = tf.Variable(tf.constant(0.1, shape=[num_filters]), name="b")
                conv = tf.nn.conv2d(
                    self.embedded_chars_expanded,
                    W,
                    strides=[1, 1, 1, 1],
                    padding="VALID",
                    name="conv")
                # Apply nonlinearity
                h = tf.nn.relu(tf.nn.bias_add(conv, b), name="relu")
                # Maxpooling over the outputs
                pooled = tf.nn.max_pool(
                    h,
                    ksize=[1, sequence_length - filter_size + 1, 1, 1],
                    strides=[1, 1, 1, 1],
                    padding='VALID',
                    name="pool")
                pooled_outputs.append(pooled)

        # Combine all the pooled features
        num_filters_total = num_filters * len(filter_sizes)
        self.h_pool = tf.concat(3, pooled_outputs)
        self.h_pool_flat = tf.reshape(self.h_pool, [-1, num_filters_total])

        # Add dropout
        with tf.name_scope("dropout"):
            self.h_drop = tf.nn.dropout(self.h_pool_flat, self.dropout_keep_prob)

        # Final (unnormalized) scores and predictions
        with tf.name_scope("output"):
            W = tf.get_variable(
                "W",
                shape=[num_filters_total, num_classes],
                initializer=tf.contrib.layers.xavier_initializer())
            b = tf.Variable(tf.constant(0.1, shape=[num_classes]), name="b")
            l2_loss += tf.nn.l2_loss(W)
            l2_loss += tf.nn.l2_loss(b)
            self.scores = tf.nn.xw_plus_b(self.h_drop, W, b, name="scores")
            self.predictions = tf.argmax(self.scores, 1, name="predictions")

        # CalculateMean cross-entropy loss
        with tf.name_scope("loss"):
            losses = tf.nn.softmax_cross_entropy_with_logits(self.scores, self.input_y)
            self.loss = tf.reduce_mean(losses) + l2_reg_lambda * l2_loss

        # Accuracy
        with tf.name_scope("accuracy"):
            correct_predictions = tf.equal(self.predictions, tf.argmax(self.input_y, 1))
            self.accuracy = tf.reduce_mean(tf.cast(correct_predictions, "float"), name="accuracy")


class ClassifierNew():
    sess = None
    vocab_processor = None
    input_x = None
    dropout_keep_prob = None
    predictions = None
    FLAGS = None

    def init_and_fit(self):

        """
        # Parameters
        # ==================================================

        # Data Parameters
        tf.flags.DEFINE_string("test", "", "Data source for the test data.")

        # Eval Parameters
        tf.flags.DEFINE_integer("embedding_dim", 300, "Dimensionality of character embedding (default: 300)")
        tf.flags.DEFINE_integer("batch_size", 64, "Batch Size (default: 64)")
        tf.flags.DEFINE_string("checkpoint_dir", "", "Checkpoint directory from training run")
        tf.flags.DEFINE_boolean("eval_train", True, "Evaluate on all training data")

        # Misc Parameters
        tf.flags.DEFINE_boolean("allow_soft_placement", True, "Allow device soft device placement")
        tf.flags.DEFINE_boolean("log_device_placement", False, "Log placement of ops on devices")
        """

        self.FLAGS = {
            'embedding_dim': 300,
            "checkpoint_dir": "./predictor_data/checkpoints",
            "allow_soft_placement": True,
            "log_device_placement": False,
            'category_labels': {1: 'conflict', 0: 'normal'}
        }
        print("Инициализация классфикатора...")
        print("\nParameters:")
        for attr, value in sorted(self.FLAGS.items()):
            print("{}={}".format(attr.upper(), value))
        print("")

        # Load vocabulary
        vocab_path = os.path.join(self.FLAGS.get('checkpoint_dir'), "..", "vocab")
        self.vocab_processor = learn.preprocessing.VocabularyProcessor.restore(vocab_path)

        # Load predictor
        checkpoint_file = tf.train.latest_checkpoint(self.FLAGS.get('checkpoint_dir'))
        graph = tf.Graph()
        with graph.as_default():
            session_conf = tf.ConfigProto(
              allow_soft_placement=self.FLAGS.get('allow_soft_placement'),
              log_device_placement=self.FLAGS.get('log_device_placement'))
            self.sess = tf.Session(config=session_conf)
            with self.sess.as_default():
                # Load the saved meta graph and restore variables
                saver = tf.train.import_meta_graph("{}.meta".format(checkpoint_file))
                saver.restore(self.sess, checkpoint_file)

                # Get the placeholders from the graph by name
                self.input_x = graph.get_operation_by_name("input_x").outputs[0]

                # input_y = graph.get_operation_by_name("input_y").outputs[0]
                self.dropout_keep_prob = graph.get_operation_by_name("dropout_keep_prob").outputs[0]

                # Tensors we want to evaluate
                self.predictions = graph.get_operation_by_name("output/predictions").outputs[0]

        print("Инициализация успешна!")

    def predict(self, data):
        x_raw = [data_helpers_conparser.clean_str_new(data)]

        x_test = np.array(list(self.vocab_processor.transform(x_raw)))

        # Collect the predictions here
        prediction = []

        prediction = self.sess.run(self.predictions, {self.input_x: x_test, self.dropout_keep_prob: 1.0})

        print('Predicted answers: ', self.FLAGS.get('category_labels')[prediction[0]], prediction[0])

        return self.FLAGS.get('category_labels')[prediction[0]], '{}-1'.format(self.FLAGS.get('category_labels')[prediction[0]])

