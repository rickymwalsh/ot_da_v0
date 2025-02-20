import os
import glob
import sys

sys.path.append('/udd/aackaouy/OT-DA/')

from unet3d.data import write_data_to_file, open_data_file
from unet3d.generator import get_training_and_validation_generators, get_validation_split
from unet3d.model import isensee2017_model
from unet3d.training import load_old_model, train_model
from unet3d.utils.utils import pickle_dump

class Test:
    def __init__(self, conf):
        self.config = conf

    def fetch_testing_data_files(self, return_subject_ids=False):
        testing_data_files = list()
        subject_ids = list()
        for subject_dir in glob.glob(
                os.path.join(os.path.dirname(__file__), '..', 'Data', 'SCSeg', '*')):
            subject_ids.append(os.path.basename(subject_dir))
            subject_files = list()
            for modality in ['crop_t2','crop_t2s','crop_lesion']:
                subject_files.append(
                    os.path.join(subject_dir, 'SC', 'res', modality + '.nii.gz'))
            testing_data_files.append(tuple(subject_files))

        if return_subject_ids:
            return testing_data_files, subject_ids
        else:
            return testing_data_files
        

    def main(self, overwrite_data=True):
        self.config.validation_split = 0.0
        self.config.data_file = os.path.abspath("Data/generated_data/" + self.config.data_set + "_testing.h5")
        self.config.training_file = os.path.abspath(
            "Data/generated_data/" + self.config.data_set + "_testing.pkl")
        self.config.validation_file = os.path.abspath(
            "Data/generated_data/" + self.config.data_set + "_testing_validation_ids.pkl")
        # convert input images into an hdf5 file
        if overwrite_data or not os.path.exists(self.config.data_file):
            testing_files, subject_ids = self.fetch_testing_data_files(return_subject_ids=True)
            write_data_to_file(testing_files, self.config.data_file, image_shape=self.config.image_shape,
                               subject_ids=subject_ids)
        data_file_opened = open_data_file(self.config.data_file)
        testing_split, _ = get_validation_split(data_file_opened, data_split=0, overwrite_data=self.config.overwrite_data,
                                                 training_file=self.config.training_file, validation_file=self.config.validation_file)
        # get training and testing generators
        # train_generator, validation_generator, n_train_steps, n_validation_steps = get_training_and_validation_generators(
        #     data_file_opened,
        #     batch_size=self.config.batch_size,
        #     data_split=self.config.validation_split,
        #     overwrite_data=overwrite_data,
        #     validation_keys_file=self.config.validation_file,
        #     training_keys_file=self.config.training_file,
        #     n_labels=self.config.n_labels,
        #     labels=self.config.labels,
        #     patch_shape=self.config.patch_shape,
        #     validation_batch_size=self.config.validation_batch_size,
        #     validation_patch_overlap=self.config.validation_patch_overlap,
        #     training_patch_start_offset=self.config.training_patch_start_offset,
        #     permute=self.config.permute,
        #     augment=self.config.augment,
        #     skip_blank=self.config.skip_blank,
        #     augment_flip=self.config.flip,
        #     augment_distortion_factor=self.config.distort)

        data_file_opened.close()