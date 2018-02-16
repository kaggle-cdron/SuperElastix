import subprocess, os, logging
from datetime import datetime

import SimpleITK as sitk, numpy as np

labelOverlapMeasurer = sitk.LabelOverlapMeasuresImageFilter();

def merge_dicts(*dicts):
    return { key: value for dict in dicts for key, value in dict.items() }

def load_vtk(file_name):
    return np.loadtxt(file_name, skiprows=5)

def load_pts(file_name):
    return np.loadtxt(file_name)

def load_point_set(file_name):
    if file_name.endswith(".vtk"):
        return load_vtk(file_name)
    else:
        return load_pts(file_name)

def pts2vtk(point_set_file_name, deformation_field_file_name):
    # Avoid name clash by appending time in microseconds. This also makes the outputted files sortable
    output_file_name = os.path.splitext(deformation_field_file_name)[0] + '_' + "{:%Y-%m-%d-%H:%M:%S.%f}".format(datetime.now()) + '.vtk'

    point_set = np.loadtxt(point_set_file_name)

    with open(output_file_name, 'w+') as f:
        f.write("# vtk DataFile Version 2.0\n")
        f.write("Point set warp generated by SuperBench\n")
        f.write("ASCII\n")
        f.write("DATASET POLYDATA\n")
        f.write("POINTS %i float\n" % point_set.shape[0])

        for point in point_set:
            for p in point:
                f.write("%f " % p)

            f.write("\n")

    return output_file_name

def warp_point_set(registration_driver, point_set_file_name, deformation_field_file_name):
    # With a slight abuse of notation in warp_point_set.json, we can use the localhost shell script to run the warping
    blueprint_file_name = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'warp_point_set.json')

    output_file_name = os.path.splitext(deformation_field_file_name)[0] + '.vtk'

    if not point_set_file_name.endswith(".vtk"):
        point_set_file_name = pts2vtk(point_set_file_name, deformation_field_file_name)

    stdout = subprocess.check_output([registration_driver,
                                      blueprint_file_name,
                                      deformation_field_file_name,
                                      point_set_file_name,
                                      output_file_name])

    return output_file_name

def warp_label_image(superelastix, label_file_name, deformation_field_file_name, output_label_file_name):
    output_label_file_name = os.path.splitext(deformation_field_file_name)[0] + '_' + "{:%Y-%m-%d-%H:%M:%S.%f}".format(datetime.now()) + '.vtk'

    try:
        stdout = subprocess.checkoutput(
            '%s --conf warp_labels.json ' +
            '--in LabelImage=%s ' +
            'DeformationField=%s ' +
            '--out WarpedLabelImage=%s ' +
            '--loglevel trace' % (
            superelastix,
            label_file_name,
            deformation_field_file_name,
            output_label_file_name))
    except:
        logging.error('Failed to warp %s.' % label_file_name)

    return output_label_file_name


def tre(registration_driver, point_set_file_names, deformation_field_file_names):
    point_set_0_to_1 = load_vtk(warp_point_set(registration_driver, point_set_file_names[0], deformation_field_file_names[0]))
    point_set_1_to_0 = load_vtk(warp_point_set(registration_driver, point_set_file_names[1], deformation_field_file_names[1]))
    point_set_0 = load_point_set(point_set_file_names[0])
    point_set_1 = load_point_set(point_set_file_names[1])
    return (
        { 'TRE': np.mean(np.sqrt(np.sum((point_set_0_to_1 - point_set_1) ** 2, -1))) },
        { 'TRE': np.mean(np.sqrt(np.sum((point_set_1_to_0 - point_set_0) ** 2, -1))) }
    )

def hausdorff(registration_driver, point_set_file_names, deformation_field_file_names):
    point_set_0_to_1 = load_vtk(warp_point_set(registration_driver, point_set_file_names[0], deformation_field_file_names[0]))
    point_set_1_to_0 = load_vtk(warp_point_set(registration_driver, point_set_file_names[1], deformation_field_file_names[1]))
    point_set_0 = load_point_set(point_set_file_names[0])
    point_set_1 = load_point_set(point_set_file_names[1])
    return (
        { 'Hausdorff': np.max(np.sqrt(np.sum((point_set_0_to_1 - point_set_1) ** 2, -1))) },
        { 'Hausdorff': np.max(np.sqrt(np.sum((point_set_1_to_0 - point_set_0) ** 2, -1))) }
    )


def singularity_ratio(deformation_field_file_names):
    deformation_field_array_0 = sitk.GetArrayViewFromImage(sitk.ReadImage(deformation_field_file_names[0]))
    deformation_field_array_1 = sitk.GetArrayViewFromImage(sitk.ReadImage(deformation_field_file_names[1]))
    return ({
        'SingularityRatio': np.sum(deformation_field_array_0 < 0)/np.prod(deformation_field_array_0.shape),
    }, {
        'SingularityRatio': np.sum(deformation_field_array_1 < 0)/np.prod(deformation_field_array_1.shape),
    })


def inverse_consistency_points(registration_driver, point_set_file_names, deformation_field_file_names):
    point_set_0_to_1_file_name = warp_point_set(registration_driver, point_set_file_names[0], deformation_field_file_names[0])
    point_set_0_to_1_to_0_file_name = warp_point_set(registration_driver, point_set_0_to_1_file_name, deformation_field_file_names[1])
    point_set_1_to_0_file_name = warp_point_set(registration_driver, point_set_file_names[1], deformation_field_file_names[1])
    point_set_1_to_0_to_0_file_name = warp_point_set(registration_driver, point_set_1_to_0_file_name, deformation_field_file_names[0])
    point_set_0 = load_point_set(point_set_file_names[0])
    point_set_1 = load_point_set(point_set_file_names[1])
    return (
        { 'InverseConsistencyTRE': np.mean(np.sqrt(np.sum((load_vtk(point_set_0_to_1_to_0_file_name) - point_set_0) ** 2, -1))) },
        { 'InverseConsistencyTRE': np.mean(np.sqrt(np.sum((load_vtk(point_set_1_to_0_to_0_file_name) - point_set_1) ** 2, -1))) }
    )


def inverse_consistency_labels(registration_driver, label_file_names, deformation_field_file_names):
    label_image_0_to_1_file_name = warp_label_image(registration_driver, label_file_names[0], deformation_field_file_names[0])
    label_image_0_to_1_to_0_file_name = warp_label_image(registration_driver, label_image_0_to_1_file_name, deformation_field_file_names[1])
    label_image_1_to_0_file_name = warp_label_image(registration_driver, label_file_names[1], deformation_field_file_names[1])
    label_image_1_to_0_to_0_file_name = warp_label_image(registration_driver, label_image_1_to_0_file_name, deformation_field_file_names[0])

    labelOverlapMeasurer.Execute(sitk.ReadImage(label_file_names[0]), sitk.ReadImage(label_image_0_to_1_to_0_file_name))
    dsc_0 = labelOverlapMeasurer.GetDiceCoefficient()

    labelOverlapMeasurer.Execute(sitk.ReadImage(label_file_names[1]), sitk.ReadImage(label_image_1_to_0_to_0_file_name))
    dsc_1 = labelOverlapMeasurer.GetDiceCoefficient()

    return (
        {'InverseConsistencyDSC': dsc_0},
        {'InverseConsistencyDSC': dsc_1}
    )


def dice(registration_driver, label_file_names, deformation_field_file_names):
    label_image_0_to_1_file_name = warp_label_image(registration_driver, label_file_names[0], deformation_field_file_names[0])
    labelOverlapMeasurer.Execute(sitk.ReadImage(label_file_names[0]), sitk.ReadImage(label_image_0_to_1_file_name))
    dsc_0 = labelOverlapMeasurer.GetDiceCoefficient()

    label_image_1_to_0_file_name = warp_label_image(registration_driver, label_file_names[1], deformation_field_file_names[1])
    labelOverlapMeasurer.Execute(sitk.ReadImage(label_file_names[1]), sitk.ReadImage(label_image_1_to_0_file_name))
    dsc_1 = labelOverlapMeasurer.GetDiceCoefficient()

    return (
        {'DSC': dsc_0},
        {'DSC': dsc_1}
    )
