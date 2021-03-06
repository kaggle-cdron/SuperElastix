import os, glob, csv, re
from abc import ABCMeta, abstractmethod
import numpy as np
from itertools import combinations

from metrics import tre, hausdorff, inverse_consistency_labels, inverse_consistency_points, dice
from util import take, sort_file_names, copy_information_from_images_to_labels, merge_dicts
from util import create_mask_by_thresholding, create_mask_by_size

# Base class for datasets. The derived classes need only to implement the file layout on disk
# and how to evaluate the dataset.  Everything else is handled by this class. See metrics.py
# for available metrics.
class Dataset(object):
    __metaclass__ = ABCMeta

    def generator(self):
        for file_name in self.file_names:
            yield file_name

    def make_shell_scripts(self, superelastix, blueprint_file_name, file_names, output_directory):
        if not os.path.exists(os.path.join(output_directory, 'sh')):
            os.mkdir(os.path.join(output_directory, 'sh'))

        # Fixed to moving
        shell_script_file_name = os.path.join(output_directory, 'sh',
                                              os.path.splitext(file_names['displacement_field_file_names'][0])[0]
                                                      .replace('/', '_').replace('\\', '_').replace('.', '_') + '.sh')

        with open(shell_script_file_name, 'w') as shell_script:
            shell_script.write('%s --conf %s --in %s %s --out DisplacementField=%s --loglevel trace --logfile %s' % (
                superelastix,
                blueprint_file_name,
                'FixedImage=%s MovingImage=%s ' % file_names['image_file_names'],
                'FixedMask=%s MovingMask=%s' % file_names['mask_file_names'] if 'mask_file_names' in file_names else ('', ''),
                os.path.join(output_directory, file_names['displacement_field_file_names'][0]),
                os.path.splitext(shell_script_file_name)[0] + '.log'))

        # Moving to fixed
        shell_script_file_name = os.path.join(output_directory, 'sh',
                                              os.path.splitext(file_names['displacement_field_file_names'][1])[0]
                                                      .replace('/', '_').replace('\\', '_').replace('.', '_') + '.sh')

        with open(shell_script_file_name, 'w') as shell_script:
            shell_script.write('%s --conf %s --in %s %s --out DisplacementField=%s --loglevel trace --logfile %s' % (
                superelastix,
                blueprint_file_name,
                'FixedImage=%s MovingImage=%s ' % (file_names['image_file_names'][1], file_names['image_file_names'][0]),
                'FixedMask=%s MovingMask=%s' % (file_names['mask_file_names'][1], file_names['mask_file_names'][0]) if 'mask_file_names' in file_names else ('', ''),
                os.path.join(output_directory, file_names['displacement_field_file_names'][1]),
                os.path.splitext(shell_script_file_name)[0] + '.log'))

    def make_batch_scripts(self):
        pass

    # The derived class should either call evaluate_point_set, evaluate_label_image
    # implement its own metrics, or combinations hereof
    @abstractmethod
    def evaluate(self):
        pass

    def evaluate_point_set(self, superelastix, file_names, output_directory):
        displacement_field_paths = (
            os.path.join(output_directory, file_names['displacement_field_file_names'][0]),
            os.path.join(output_directory, file_names['displacement_field_file_names'][1]),
        )

        tre_0, tre_1 = tre(
            superelastix,
            file_names['ground_truth_file_names'],
            displacement_field_paths)
        hausdorff_0, hausdorff_1 = hausdorff(superelastix,
            file_names['ground_truth_file_names'],
            displacement_field_paths)
        inverse_consistency_points_0, inverse_consistency_points_1 = inverse_consistency_points(
            superelastix,
            file_names['ground_truth_file_names'],
            displacement_field_paths)

        return {
            file_names['displacement_field_file_names'][0]: merge_dicts(tre_0, hausdorff_0, inverse_consistency_points_0),
            file_names['displacement_field_file_names'][1]: merge_dicts(tre_1, hausdorff_1, inverse_consistency_points_1)
        }

    # Default evaluation method for label ground truths
    def evaluate_label_image(self, superelastix, file_names, output_directory):
        displacement_field_paths = (
            os.path.join(output_directory, file_names['displacement_field_file_names'][0]),
            os.path.join(output_directory, file_names['displacement_field_file_names'][1]),
        )

        inverse_consistency_atlas_0, inverse_consistency_atlas_1 = inverse_consistency_labels(
            superelastix,
            file_names['ground_truth_file_names'],
            displacement_field_paths)

        dice_0, dice_1 = dice(superelastix,
            file_names['ground_truth_file_names'],
            displacement_field_paths)

        return {
            file_names['displacement_field_file_names'][0]: merge_dicts(inverse_consistency_atlas_0, dice_0),
            file_names['displacement_field_file_names'][1]: merge_dicts(inverse_consistency_atlas_1, dice_1)
        }


class CUMC12(Dataset):
    def __init__(self, input_directory, output_directory, max_number_of_registrations):
        self.name = 'CUMC12'
        self.category = 'Brain'

        self.input_directory = input_directory
        file_names = []

        image_file_names = [os.path.join(input_directory, 'Heads', image) for image in os.listdir(os.path.join(input_directory, 'Heads')) if image.endswith('.hdr')]
        image_file_names = [pair for pair in combinations(image_file_names, 2)]

        label_file_names = [os.path.join(input_directory, 'Atlases', atlas) for atlas in os.listdir(os.path.join(input_directory, 'Atlases')) if atlas.endswith('.hdr')]
        label_file_names = [pair for pair in combinations(label_file_names, 2)]

        displacement_field_file_names = []
        for image_file_name_0, image_file_name_1 in image_file_names:
            image_file_name_0 = os.path.basename(image_file_name_0)
            image_file_name_1 = os.path.basename(image_file_name_1)
            image_file_name_we_0, image_extension_we_0 = os.path.splitext(image_file_name_0)
            image_file_name_we_1, image_extension_we_1 = os.path.splitext(image_file_name_1)
            displacement_field_file_names.append((os.path.join(self.name, image_file_name_we_1 + "_to_" + image_file_name_we_0 + ".nii.gz"),
                                                  os.path.join(self.name, image_file_name_we_0 + "_to_" + image_file_name_we_1 + ".nii.gz")))

        mask_file_names = [create_mask_by_thresholding(label_file_name_pair, displacement_field_file_name_pair, output_directory, 0., 32, 16)
                           for label_file_name_pair, displacement_field_file_name_pair in zip(label_file_names, displacement_field_file_names)]

        for image_file_name, mask_file_name, label_file_name, displacement_field_file_name in zip(image_file_names, mask_file_names, label_file_names, displacement_field_file_names):
            file_names.append({
                'image_file_names': image_file_name,
                'mask_file_names': mask_file_name,
                'ground_truth_file_names': label_file_name,
                'displacement_field_file_names': displacement_field_file_name
            })

        self.file_names = take(sort_file_names(file_names), max_number_of_registrations // 2)

    def evaluate(self, superelastix, file_names, output_directory):
        return self.evaluate_label_image(superelastix, file_names, output_directory)


class DIRLAB(Dataset):
    def __init__(self, input_directory, mask_directory, output_directory, max_number_of_registrations):
        self.name = 'DIRLAB'
        self.category = 'Lung'

        self.input_directory = input_directory
        file_names = []

        # DIR-LAB provides raw binary image only so we write mhd header files for loading the data.
        # The image information was retrieved from https://www.dir-lab.com/ReferenceData.html
        dirlab_image_information_file_name = os.path.join(os.path.dirname(__file__), "dirlab_image_information.csv")

        # Find corresponding subdirectory which contains the id and associate it with this line of the csv file.
        # TODO: Maybe not the prettiest approach
        sub_directories = [directory for directory in os.listdir(self.input_directory) if os.path.isdir(os.path.join(input_directory, directory))]
        sub_directory_ids = list(map(lambda str: int(re.search(r'\d+', str).group()), sub_directories))
        dirlab_image_information = dict()
        for image_information in csv.DictReader(open(dirlab_image_information_file_name)):
            dirlab_image_information[image_information['id']] = image_information
            dirlab_image_information[image_information['id']]['sub_directory'] = sub_directories[sub_directory_ids.index(int(image_information['id']))]

        # Now we have all the information necessary so generate the header files
        for id in dirlab_image_information:
            img_0_file_name = glob.glob(os.path.join(input_directory, dirlab_image_information[id]['sub_directory'], 'Images', '*T00*.img'))[0]
            img_1_file_name = glob.glob(os.path.join(input_directory, dirlab_image_information[id]['sub_directory'], 'Images', '*T50*.img'))[0]

            # Write mhd header files
            os.makedirs(os.path.join(output_directory, 'tmp', 'images', self.name), exist_ok=True)
            mhd_0_file_name = os.path.join(output_directory, 'tmp', 'images', self.name, os.path.splitext(os.path.basename(img_0_file_name))[0] + '.mhd')
            with open(mhd_0_file_name, 'w') as mhd:
                mhd.write('ObjectType = Image\n')
                mhd.write('NDims = 3\n')
                mhd.write('BinaryData = True\n')
                mhd.write('DimSize = %s %s %s\n' % (dirlab_image_information[id]['x_size'], dirlab_image_information[id]['y_size'], dirlab_image_information[id]['z_size']))
                mhd.write('ElementSpacing = %s %s %s\n' % (dirlab_image_information[id]['x_spacing'], dirlab_image_information[id]['y_spacing'], dirlab_image_information[id]['z_spacing']))
                mhd.write('ElementType = MET_USHORT\n')
                mhd.write('ElementDataFile = %s\n' % img_0_file_name)

            mhd_1_file_name = os.path.join(output_directory, 'tmp', 'images', self.name, os.path.splitext(os.path.basename(img_1_file_name))[0] + '.mhd')
            with open(mhd_1_file_name, 'w') as mhd:
                mhd.write('ObjectType = Image\n')
                mhd.write('NDims = 3\n')
                mhd.write('BinaryData = True\n')
                mhd.write('DimSize = %s %s %s\n' % (dirlab_image_information[id]['x_size'], dirlab_image_information[id]['y_size'], dirlab_image_information[id]['z_size']))
                mhd.write('ElementSpacing = %s %s %s\n' % (dirlab_image_information[id]['x_spacing'], dirlab_image_information[id]['y_spacing'], dirlab_image_information[id]['z_spacing']))
                mhd.write('ElementType = MET_USHORT\n')
                mhd.write('ElementDataFile = %s\n' % img_1_file_name)

            point_set_0 = glob.glob(os.path.join(input_directory, dirlab_image_information[id]['sub_directory'], 'ExtremePhases', '*T00_xyz.txt'))[0]
            point_set_1 = glob.glob(os.path.join(input_directory, dirlab_image_information[id]['sub_directory'], 'ExtremePhases', '*T50_xyz.txt'))[0]

            displacement_field_file_name_0 = os.path.join(self.name, dirlab_image_information[id]['sub_directory'], '50_to_00.nii.gz')
            displacement_field_file_name_1 = os.path.join(self.name, dirlab_image_information[id]['sub_directory'], '00_to_50.nii.gz')

            image_file_names = (mhd_0_file_name, mhd_1_file_name)
            point_set_file_names = (point_set_0, point_set_1)
            displacement_field_file_names = (displacement_field_file_name_0, displacement_field_file_name_1)

            if mask_directory is not None and os.path.exists(mask_directory):
                mask_file_names = (os.path.join(mask_directory, dirlab_image_information[id]['sub_directory'], 'Images', os.path.basename(mhd_0_file_name)),
                                   os.path.join(mask_directory, dirlab_image_information[id]['sub_directory'], 'Images', os.path.basename(mhd_1_file_name)))
            else:
                # If no mask was provided, just generate mask filled with ones
                mask_file_names = (
                    create_mask_by_size(image_file_names[0], os.path.join(output_directory, 'tmp', 'masks', displacement_field_file_names[0])),
                    create_mask_by_size(image_file_names[1], os.path.join(output_directory, 'tmp', 'masks', displacement_field_file_names[1]))
                )

            file_names.append({
                'image_file_names': image_file_names,
                'mask_file_names': mask_file_names,
                'ground_truth_file_names': point_set_file_names,
                'displacement_field_file_names': displacement_field_file_names
            })

        self.file_names = take(sort_file_names(file_names), max_number_of_registrations // 2)

    def evaluate(self, superelastix, file_names, output_directory):
        return self.evaluate_point_set(superelastix, file_names, output_directory)


class EMPIRE(Dataset):
    def __init__(self, input_directory, max_number_of_registrations):
        self.name = 'EMPIRE'
        self.category = 'Lung'

        file_names = []

        for i in range(1, 31):
            image_file_names = (os.path.join(input_directory, 'scans', "%02d" % i + '_Fixed.mhd'),
                                os.path.join(input_directory, 'scans', "%02d" % i + '_Moving.mhd'))

            mask_file_names = (os.path.join(input_directory, 'lungMasks', "%02d" % i + '_Fixed.mhd'),
                               os.path.join(input_directory, 'lungMasks', "%02d" % i + '_Moving.mhd'))

            # TODO: Find out output format
            displacement_field_file_names = (os.path.join(self.name, "%02d" % i + '_Moving_to_Fixed.nii.gz'),
                                             os.path.join(self.name, "%02d" % i + '_Fixed_to_Moving.nii.gz'))

            file_names.append({
                'image_file_names': image_file_names,
                'mask_file_names': mask_file_names,
                'displacement_field_file_names': displacement_field_file_names
            })

        self.file_names = take(sort_file_names(file_names), max_number_of_registrations // 2)


    def evaluate(self, superelastix, file_names, output_directory):
        # TODO: Submit to EMPIRE
        pass


class ISBR18(Dataset):
    def __init__(self, input_directory, output_directory, max_number_of_registrations):
        self.name = 'ISBR18'
        self.category = 'Brain'

        self.input_directory = input_directory
        file_names = []

        image_file_names = [os.path.join(input_directory, 'Heads', image)
                            for image in os.listdir(os.path.join(input_directory, 'Heads'))
                            if image.endswith('.hdr')]
        image_file_names = [pair for pair in combinations(image_file_names, 2)]

        label_file_names = [os.path.join(input_directory, 'Atlases', atlas)
                            for atlas in os.listdir(os.path.join(input_directory, 'Atlases'))
                            if atlas.endswith('.hdr') and not "copied-information" in atlas]
        label_file_names = [pair for pair in combinations(label_file_names, 2)]

        displacement_field_file_names = []
        for image_file_name_0, image_file_name_1 in image_file_names:
            image_file_name_0 = os.path.basename(image_file_name_0)
            image_file_name_1 = os.path.basename(image_file_name_1)
            image_file_name_we_0, image_extension_we_0 = os.path.splitext(image_file_name_0)
            image_file_name_we_1, image_extension_we_1 = os.path.splitext(image_file_name_1)
            displacement_field_file_names.append((os.path.join(self.name, image_file_name_we_1 + "_to_" + image_file_name_we_0 + ".nii.gz"),
                                                  os.path.join(self.name, image_file_name_we_0 + "_to_" + image_file_name_we_1 + ".nii.gz")))

        # These label images do not have any world coordinate information
        label_file_names = [copy_information_from_images_to_labels(image_file_name_pair,
                                                                   label_file_name_pair,
                                                                   displacement_field_file_name_pair,
                                                                   output_directory,
                                                                   'MET_USHORT')
                            for image_file_name_pair,
                                label_file_name_pair,
                                displacement_field_file_name_pair in zip(image_file_names,
                                                                         label_file_names,
                                                                         displacement_field_file_names)]

        mask_file_names = [create_mask_by_thresholding(label_file_name_pair, displacement_field_file_name_pair, output_directory, 0., 32, 16)
                           for label_file_name_pair, displacement_field_file_name_pair in zip(label_file_names, displacement_field_file_names)]

        for image_file_name, mask_file_name, label_file_name, displacement_field_file_name in zip(image_file_names, mask_file_names, label_file_names, displacement_field_file_names):
            file_names.append({
                'image_file_names': image_file_name,
                'mask_file_names': mask_file_name,
                'ground_truth_file_names': label_file_name,
                'displacement_field_file_names': displacement_field_file_name
            })

        self.file_names = take(sort_file_names(file_names), max_number_of_registrations // 2)

    # TODO: Find out why inverse consistency does not work with this dataset
    def evaluate(self, superelastix, file_names, output_directory):

        displacement_field_paths = (
            os.path.join(output_directory, file_names['displacement_field_file_names'][0]),
            os.path.join(output_directory, file_names['displacement_field_file_names'][1]),
        )

        dice_0, dice_1 = dice(superelastix,
                              file_names['ground_truth_file_names'],
                              displacement_field_paths)

        return {
            file_names['displacement_field_file_names'][0]: dice_0,
            file_names['displacement_field_file_names'][1]: dice_1
        }


class LPBA40(Dataset):
    def __init__(self, input_directory, output_directory, max_number_of_registrations):
        self.name = 'LPBA40'
        self.category = 'Brain'

        self.input_directory = input_directory
        file_names = []

        image_file_names = [glob.glob(os.path.join(self.input_directory,
                                                   'delineation_space',
                                                   sub_directory,
                                                   '*.delineation.skullstripped.hdr'))[0]
                            for sub_directory in os.listdir(os.path.join(self.input_directory,
                                                                         'delineation_space'))
                            if os.path.isdir(os.path.join(self.input_directory,
                                                          'delineation_space',
                                                          sub_directory))]

        image_file_names = [pair for pair in combinations(image_file_names, 2)]

        label_file_names = [glob.glob(os.path.join(self.input_directory,
                                                   'delineation_space',
                                                   sub_directory,
                                                   '*.delineation.structure.label.hdr'))[0]
                            for sub_directory in os.listdir(os.path.join(self.input_directory,
                                                                         'delineation_space'))
                            if os.path.isdir(os.path.join(self.input_directory,
                                                          'delineation_space',
                                                          sub_directory))]

        label_file_names = [pair for pair in combinations(label_file_names, 2)]

        displacement_field_file_names = []
        for image_file_name_0, image_file_name_1 in image_file_names:
            image_file_name_0 = os.path.basename(image_file_name_0)
            image_file_name_1 = os.path.basename(image_file_name_1)
            image_file_name_we_0 = os.path.splitext(image_file_name_0)[0]
            image_file_name_we_1 = os.path.splitext(image_file_name_1)[0]
            displacement_field_file_names.append((os.path.join(self.name, image_file_name_we_1 + "_to_" + image_file_name_we_0 + ".nii.gz"),
                                                  os.path.join(self.name, image_file_name_we_0 + "_to_" + image_file_name_we_1 + ".nii.gz")))

        mask_file_names = [create_mask_by_thresholding(label_file_name_pair, displacement_field_file_name_pair, output_directory, 0., 2, 2)
                           for label_file_name_pair, displacement_field_file_name_pair in zip(label_file_names, displacement_field_file_names)]

        for image_file_name, mask_file_name, label_file_name, displacement_field_file_name in zip(image_file_names, mask_file_names, label_file_names, displacement_field_file_names):
            file_names.append({
                'image_file_names': image_file_name,
                'mask_file_names': mask_file_name,
                'ground_truth_file_names': label_file_name,
                'displacement_field_file_names': displacement_field_file_name
            })

        self.file_names = take(sort_file_names(file_names), max_number_of_registrations // 2)

    def evaluate(self, superelastix, file_names, output_directory):
        return self.evaluate_label_image(superelastix, file_names, output_directory)


class MGH10(Dataset):
    def __init__(self, input_directory, output_directory, max_number_of_registrations):
        self.name = 'MGH10'
        self.category = 'Brain'

        self.input_directory = input_directory
        file_names = []

        image_file_names = [os.path.join(input_directory, 'Heads', image) for image in
                            os.listdir(os.path.join(input_directory, 'Heads')) if image.endswith('.hdr')]
        image_file_names = [pair for pair in combinations(image_file_names, 2)]

        label_file_names = [os.path.join(input_directory, 'Atlases', atlas) for atlas in
                            os.listdir(os.path.join(input_directory, 'Atlases')) if atlas.endswith('.hdr')]
        label_file_names = [pair for pair in combinations(label_file_names, 2)]

        displacement_field_file_names = []
        for image_file_name_0, image_file_name_1 in image_file_names:
            image_file_name_0 = os.path.basename(image_file_name_0)
            image_file_name_1 = os.path.basename(image_file_name_1)
            image_file_name_we_0, image_extension_we_0 = os.path.splitext(image_file_name_0)
            image_file_name_we_1, image_extension_we_1 = os.path.splitext(image_file_name_1)
            displacement_field_file_names.append(
                (os.path.join(self.name, image_file_name_we_1 + "_to_" + image_file_name_we_0 + ".nii.gz"),
                 os.path.join(self.name, image_file_name_we_0 + "_to_" + image_file_name_we_1 + ".nii.gz")))


        # Label images do not have any world coordinate information
        label_file_names = [copy_information_from_images_to_labels(image_file_name_pair,
                                                                   label_file_name_pair,
                                                                   displacement_field_file_name_pair,
                                                                   output_directory,
                                                                   'MET_USHORT')
                            for image_file_name_pair, label_file_name_pair, displacement_field_file_name_pair
                            in zip(image_file_names, label_file_names, displacement_field_file_names)]

        mask_file_names = [create_mask_by_thresholding(label_file_name_pair, displacement_field_file_name_pair, output_directory, 0., 32, 16)
                           for label_file_name_pair, displacement_field_file_name_pair in zip(label_file_names, displacement_field_file_names)]

        for image_file_name, mask_file_name, label_file_name, displacement_field_file_name in zip(image_file_names, mask_file_names, label_file_names, displacement_field_file_names):
            file_names.append({
                'image_file_names': image_file_name,
                'mask_file_names': mask_file_name,
                'ground_truth_file_names': label_file_name,
                'displacement_field_file_names': displacement_field_file_name
            })

        self.file_names = take(sort_file_names(file_names), max_number_of_registrations // 2)

    def evaluate(self, superelastix, file_names, output_directory):
        return self.evaluate_label_image(superelastix, file_names, output_directory)


class POPI(Dataset):
    def __init__(self, input_directory, mask_directory, output_directory, max_number_of_registrations):
        self.name = 'POPI'
        self.category = 'Lung'

        self.input_directory = input_directory
        file_names = []

        sub_directories = [directory for directory in os.listdir(self.input_directory) if os.path.isdir(os.path.join(input_directory, directory))]

        for sub_directory in sub_directories:
            image_file_names = (os.path.join(input_directory, sub_directory, 'mhd', '00.mhd'),
                                os.path.join(input_directory, sub_directory, 'mhd', '50.mhd'))
            point_set_file_names = (os.path.join(input_directory, sub_directory, 'pts', '00.pts'),
                                    os.path.join(input_directory, sub_directory, 'pts', '50.pts'))
            displacement_field_file_names = (os.path.join(self.name, sub_directory, '50_to_00.nii.gz'),
                                             os.path.join(self.name, sub_directory, '00_to_50.nii.gz'))

            if mask_directory is not None and os.path.exists(mask_directory):
                mask_file_names = (os.path.join(mask_directory, sub_directory, 'mhd', '00.mhd'),
                                   os.path.join(mask_directory, sub_directory, 'mhd', '50.mhd'))
            else:
                # If no mask was provided, just generate mask filled with ones
                mask_file_names = (
                    create_mask_by_size(image_file_names[0], os.path.join(output_directory, 'tmp', 'masks', displacement_field_file_names[0])),
                    create_mask_by_size(image_file_names[1], os.path.join(output_directory, 'tmp', 'masks', displacement_field_file_names[1]))
                )

            file_names.append({
                "image_file_names": image_file_names,
                "mask_file_names": mask_file_names,
                "ground_truth_file_names": point_set_file_names,
                "displacement_field_file_names": displacement_field_file_names
            })

        self.file_names = take(sort_file_names(file_names), max_number_of_registrations // 2)

    def evaluate(self, superelastix, file_names, output_directory):
        return self.evaluate_point_set(superelastix, file_names, output_directory)


class SPREAD(Dataset):
    def __init__(self, input_directory, output_directory, max_number_of_registrations):
        self.name = 'SPREAD'
        self.category = 'Lung'

        self.input_directory = input_directory
        file_names = []

        sub_directories = [directory
                           for directory in os.listdir(os.path.join(self.input_directory, 'mhd'))
                           if os.path.isdir(os.path.join(self.input_directory, 'mhd', directory))]

        for sub_directory in sub_directories:
            image_file_names = (os.path.join(input_directory, 'mhd', sub_directory, 'baseline_1.mha'),
                                os.path.join(input_directory, 'mhd', sub_directory, 'followup_1.mha'))

            os.makedirs(os.path.join(output_directory, self.name), exist_ok=True)

            baseline_point_set_file_name_we = os.path.join(input_directory, 'groundtruth', 'distinctivePoints', sub_directory + '_baseline_1_Cropped_point')
            point_set = np.loadtxt(baseline_point_set_file_name_we + '.txt', skiprows=2)
            baseline_point_set_file_name_we_without_header = os.path.join(output_directory, 'tmp', self.name, sub_directory + '_baseline_1_Cropped_point.txt')
            np.savetxt(baseline_point_set_file_name_we_without_header, point_set)

            follow_up_point_set_file_name_we = os.path.join(input_directory, 'groundtruth', 'annotate', 'Consensus', sub_directory + '_b1f1_point')
            point_set = np.loadtxt(follow_up_point_set_file_name_we + '.txt', skiprows=2)
            follow_up_point_set_file_name_we_without_header = os.path.join(output_directory, 'tmp', self.name, sub_directory + '_baseline_1_Cropped_point.txt')
            np.savetxt(follow_up_point_set_file_name_we_without_header, point_set)


            point_set_file_names = (baseline_point_set_file_name_we_without_header,
                                    follow_up_point_set_file_name_we_without_header)

            displacement_field_file_names = (os.path.join(self.name, sub_directory, 'followup_to_baseline.nii.gz'),
                                             os.path.join(self.name, sub_directory, 'baseline_to_followup.nii.gz'))

            file_names.append({
                "image_file_names": image_file_names,
                "ground_truth_file_names": point_set_file_names,
                "displacement_field_file_names": displacement_field_file_names
            })

        self.file_names = take(sort_file_names(file_names), max_number_of_registrations // 2)


    def evaluate(self, superelastix, file_names, output_directory):
        self.evaluate_point_set(superelastix, file_names, output_directory)
