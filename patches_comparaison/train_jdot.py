import os
import glob
import sys

# sys.path.append('/udd/aackaouy/OT-DA/')

from unet3d.data import write_data_to_file, open_data_file
from unet3d.model import isensee2017_model
from patches_comparaison.JDOT import JDOT

class Train_JDOT:
    """
    Class that handles the training and testing of JDOT.
    The self.config object contains all information on the configuration (cf config.py).
    """
    def __init__(self, conf):
        self.config = conf


    def main(self, overwrite_data=True, overwrite_model=True):
        # convert input images into an hdf5 file
        if overwrite_data or not os.path.exists(self.config.source_data_file) or not os.path.exists(self.config.target_data_file):
            '''
            We write two files, one with source samples and one with target samples.
            '''
            source_data_files, target_data_files, subject_ids_source, subject_ids_target = self.fetch_training_data_files(return_subject_ids=True)

            if not os.path.exists(self.config.source_data_file) or overwrite_data:
                write_data_to_file(source_data_files, self.config.source_data_file, image_shape=self.config.image_shape,
                               subject_ids=subject_ids_source)
            if not os.path.exists(self.config.target_data_file) or overwrite_data:
                write_data_to_file(target_data_files, self.config.target_data_file, image_shape=self.config.image_shape,
                               subject_ids=subject_ids_target)
        else:
            print("Reusing previously written data file. Set overwrite_data to True to overwrite this file.")

        source_data = open_data_file(self.config.source_data_file)
        target_data = open_data_file(self.config.target_data_file)


        # instantiate new model, compile = False because the compilation is made in JDOT.py

        model, context_output_name = isensee2017_model(input_shape=self.config.input_shape, n_labels=self.config.n_labels,
                                      initial_learning_rate=self.config.initial_learning_rate,
                                      n_base_filters=self.config.n_base_filters,
                                      loss_function=self.config.loss_function,
                                      shortcut=self.config.shortcut,
                                      depth=self.config.depth,
                                      compile=False)
        # get training and testing generators
        if not self.config.depth_jdot:
            context_output_name = []
        jd = JDOT(model, config=self.config, source_data=source_data, target_data=target_data, context_output_name=context_output_name)
        # m = jd.load_old_model(self.config.model_file)
        # print(m)
        if self.config.load_base_model:
            print("Loading trained model")
            jd.load_old_model(os.path.abspath("Data/saved_models/model_center_"+self.config.source_center)+".h5")
        elif not self.config.overwrite_model:
            jd.load_old_model(self.config.model_file)
        else:
            print("Creating new model, this will overwrite your old model")
        jd.compile_model()
        if self.config.train_jdot:
            jd.train_model(self.config.epochs)
        else:
            jd.train_model_on_source(self.config.epochs)
        jd.evaluate_model()

        source_data.close()
        target_data.close()

    def fetch_training_data_files(self, return_subject_ids=False):
        '''
        Function to get the training files from the source and from the target.
        We write the source and target samples in two different files
        :param return_subject_ids:
        :return:
        '''
        source_data_files = list()
        target_data_files = list()
        subject_ids_source = list()
        subject_ids_target = list()
        for subject_dir in glob.glob(
                # os.path.join(os.path.dirname(__file__), "../Data/data_" + self.config.data_set, "training", "*")):
                os.path.join(os.path.dirname(__file__), '..', 'Data', 'SCSeg', '*')):
            
            subject_ids_source.append(os.path.basename(subject_dir))
            subject_files = list()
            for modality in ['crop_t2','crop_t2s','crop_lesion']:
                subject_files.append(
                    os.path.join(subject_dir, 'SC', 'res', modality + '.nii.gz'))
            source_data_files.append(tuple(subject_files))
            
            subject_ids_target.append(os.path.basename(subject_dir))
            subject_files = list()
            for modality in ['crop_t2','crop_t2s','crop_lesion']:
                subject_files.append(
                    os.path.join(subject_dir, 'SC', 'res', modality + '.nii.gz'))
            target_data_files.append(tuple(subject_files))
    
        if return_subject_ids:
            return source_data_files, target_data_files, subject_ids_source, subject_ids_target
        else:
            return source_data_files, target_data_files
    
