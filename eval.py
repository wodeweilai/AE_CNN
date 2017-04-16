#! /usr/bin/env python

import csv
import os
import data_helpers
import numpy as np
import tensorflow as tf
from tensorflow.contrib import learn
from sklearn.metrics import precision_score, recall_score, f1_score


# Parameters
# ==================================================

# Data Parameters
tf.flags.DEFINE_string("review_data_file", "./data/reviews_test.txt", "Reviews.")
tf.flags.DEFINE_string("label_data_file", "./data/labels_test.txt", "Labels.")
tf.flags.DEFINE_string("multilabel_test_data", "data/test_data.csv", "Data source for the Reviews.")

# Eval Parameters
tf.flags.DEFINE_integer("batch_size", 48, "Batch Size (default: 64)")
tf.flags.DEFINE_string("checkpoint_dir", "./runs/ /checkpoints", "Checkpoint directory from training run")
tf.flags.DEFINE_boolean("eval_train", True, "Evaluate on all training data")

# Misc Parameters
tf.flags.DEFINE_boolean("allow_soft_placement", True, "Allow device soft device placement")
tf.flags.DEFINE_boolean("log_device_placement", False, "Log placement of ops on devices")


FLAGS = tf.flags.FLAGS
FLAGS._parse_flags()
print("\nParameters:")
for attr, value in sorted(FLAGS.__flags.items()):
    print("{}={}".format(attr.upper(), value))
print("")

# CHANGE THIS: Load data. Load your own data here
if FLAGS.eval_train:
    x_raw, y_raw = data_helpers.load_data_multilabel(FLAGS.multilabel_test_data)
    # x_raw, y_test = data_helpers.load_data_and_labels(FLAGS.review_data_file, FLAGS.label_data_file)
    y_test = np.argmax(y_raw, axis=1)
else:
    x_raw = ["a masterpiece four years in the making", "everything is off."]
    y_test = [1, 0]

# Map data into vocabulary
vocab_path = os.path.join(FLAGS.checkpoint_dir, "..", "vocab")
vocab_processor = learn.preprocessing.VocabularyProcessor.restore(vocab_path)
x_test = np.array(list(vocab_processor.transform(x_raw)))

print("\nEvaluating...\n")

# Evaluation
# ==================================================
checkpoint_file = tf.train.latest_checkpoint(FLAGS.checkpoint_dir)
graph = tf.Graph()
with graph.as_default():
    session_conf = tf.ConfigProto(
      allow_soft_placement=FLAGS.allow_soft_placement,
      log_device_placement=FLAGS.log_device_placement)
    sess = tf.Session(config=session_conf)
    with sess.as_default():
        # Load the saved meta graph and restore variables
        saver = tf.train.import_meta_graph("{}.meta".format(checkpoint_file))
        saver.restore(sess, checkpoint_file)

        # Get the placeholders from the graph by name
        input_x = graph.get_operation_by_name("input_x").outputs[0]
        # input_y = graph.get_operation_by_name("input_y").outputs[0]
        dropout_keep_prob = graph.get_operation_by_name("dropout_keep_prob").outputs[0]

        # Tensors we want to evaluate
        predictions = graph.get_operation_by_name("output/predictions").outputs[0]
        scores = graph.get_operation_by_name("output/scores").outputs[0]


        # Generate batches for one epoch
        batches = data_helpers.batch_iter(list(x_test), FLAGS.batch_size, 1, shuffle=False)

        # Collect the predictions here
        all_predictions = []
        all_scores = np.empty([0, 13])
        for x_test_batch in batches:
            batch_predictions = sess.run(predictions, {input_x: x_test_batch, dropout_keep_prob: 1.0})
            all_predictions = np.concatenate([all_predictions, batch_predictions])
            batch_scores = sess.run(scores, {input_x: x_test_batch, dropout_keep_prob: 1.0})
            all_scores = np.concatenate([all_scores, batch_scores])

# Print accuracy if y_test is defined
if y_test is not None:
    correct_predictions = float(sum(all_predictions == y_test))
    print("Total number of test examples: {}".format(len(y_test)))
    print("Accuracy: {:g}".format(correct_predictions/float(len(y_test))))

print ("Precision", precision_score(y_test, all_predictions,average='micro'))
print ("Recall", recall_score(y_test, all_predictions,average='micro'))
print("f1_score", f1_score(y_test, all_predictions,average='weighted'))

# Save the evaluation to a csv
predictions_human_readable = np.column_stack((np.array(x_raw), all_predictions, y_test))
out_path = os.path.join(FLAGS.checkpoint_dir, "..", "prediction.csv")
print("Saving evaluation to {0}".format(out_path))
with open(out_path, 'w') as f:
    csv.writer(f).writerows(predictions_human_readable)

# Save the evaluation to a csv
predictions_human_readable = np.column_stack((all_scores, all_predictions, y_raw,y_test))
out_path = os.path.join(FLAGS.checkpoint_dir, "..", "scores.csv")
print("Saving evaluation to {0}".format(out_path))
with open(out_path, 'w') as f:
    csv.writer(f).writerows(predictions_human_readable)
