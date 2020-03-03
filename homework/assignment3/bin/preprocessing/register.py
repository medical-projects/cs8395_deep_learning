# Register all volumes to 0022.nii.gz
import ants
import os

# Constants for path names
FIXED_IMG = "/content/drive/My Drive/cs8395_deep_learning/assignment3/data/Train/img/0007.nii.gz"
OLD_TRAIN_IMG = "/content/drive/My Drive/cs8395_deep_learning/assignment3/data/Train/img/"
NEW_TRAIN_IMG = "/content/drive/My Drive/cs8395_deep_learning/assignment3/data/Train/img_registered/"
OLD_TRAIN_LABELS = "/content/drive/My Drive/cs8395_deep_learning/assignment3/data/Train/label/"
NEW_TRAIN_LABELS = "/content/drive/My Drive/cs8395_deep_learning/assignment3/data/Train/label_registered/"
OLD_VAL_IMG = "/content/drive/My Drive/cs8395_deep_learning/assignment3/data/Val/img/"
NEW_VAL_IMG = "/content/drive/My Drive/cs8395_deep_learning/assignment3/data/Val/img_registered/"
OLD_VAL_LABELS = "/content/drive/My Drive/cs8395_deep_learning/assignment3/data/Val/label/"
NEW_VAL_LABELS = "/content/drive/My Drive/cs8395_deep_learning/assignment3/data/Val/label_registered/"

fixed = ants.image_read(FIXED_IMG)

# Register all the training images
for file_name in os.listdir(OLD_TRAIN_IMG):
    moving = ants.image_read(OLD_TRAIN_IMG + file_name)
    label = ants.image_read(OLD_TRAIN_LABELS + file_name)
    transform = ants.registration(fixed=fixed , moving=moving ,
                                 type_of_transform = 'Affine' )
    transformed_image = ants.apply_transforms( fixed=fixed, moving=moving,
                                               transformlist=transform['fwdtransforms'],
                                               interpolator  = 'nearestNeighbor')
    transformed_image.to_file(NEW_TRAIN_IMG + file_name)
    transformed_label = ants.apply_transforms( fixed=fixed, moving=label,
                                               transformlist=transform['fwdtransforms'],
                                               interpolator  = 'nearestNeighbor')
    transformed_label.to_file(NEW_TRAIN_LABELS + file_name)

# Repeat for the validation images
for file_name in os.listdir(OLD_VAL_IMG):
    moving = ants.image_read(OLD_VAL_IMG + file_name)
    label = ants.image_read(OLD_VAL_LABELS + file_name)
    transform = ants.registration(fixed=fixed , moving=moving ,
                                 type_of_transform = 'Affine' )
    transformed_image = ants.apply_transforms( fixed=fixed, moving=moving,
                                               transformlist=transform['fwdtransforms'],
                                               interpolator  = 'nearestNeighbor')
    transformed_image.to_file(NEW_VAL_IMG + file_name)
    transformed_label = ants.apply_transforms( fixed=fixed, moving=label,
                                               transformlist=transform['fwdtransforms'],
                                               interpolator  = 'nearestNeighbor')
    transformed_label.to_file(NEW_VAL_LABELS + file_name)