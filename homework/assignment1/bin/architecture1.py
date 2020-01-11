# Imports for Pytorch
from __future__ import print_function
import argparse
import numpy as np
import pandas as pd
import os
import torch
from torch.utils.data import Dataset, DataLoader
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torchvision import datasets, transforms
from torch.optim.lr_scheduler import StepLR
from skimage import io, transform

# Class for the dataset
class DetectionImages(Dataset):
    def __init__(self, csv_file, root_dir, transform=None):
        """
        Args:
            csv_file (string): Path to the csv file with annotations.
            root_dir (string): Directory with all the images.
            transform (callable, optional): Optional transform to be applied
                on a sample.
        """
        self.labels_df = pd.read_csv(csv_file, sep=" ", header=None)
        self.root_dir = root_dir
        self.transform = transform

    def __len__(self):
        return len(self.labels_df)

    def __getitem__(self, idx):
        if torch.is_tensor(idx):
            idx = idx.tolist()

        img_name = os.path.join(self.root_dir,
                                self.labels_df.iloc[idx, 0])
        image = io.imread(img_name)
        label = self.labels_df.iloc[idx, 1:]
        label = np.array([label])
        label = label.astype('float').reshape(-1, 2)
        sample = {'image': image, 'label': label}

        if self.transform:
            sample = self.transform(sample)

        return sample

class ToTensor(object):
    """Convert ndarrays in sample to Tensors."""

    def __call__(self, sample):
        image, label = sample['image'], sample['label']

        # swap color axis because
        # numpy image: H x W x C
        # torch image: C X H X W
        image = image.transpose((2, 0, 1))
        label = label.reshape(-1)
        return {'image': torch.from_numpy(image),
                'label': torch.from_numpy(label)}

# Define the neural network
class Net(nn.Module):
    # Define the dimensions for each layer.
    def __init__(self):
        super(Net, self).__init__()
        # First convolutional layer has 3 input channels, 15 output channels,
        # a 3x3 square kernel, and a stride of 1.
        self.conv1 = nn.Conv2d(3, 15, 3, 1)
        # Second convolutional layer has 30 input channels, 30 output channels,
        # a 3x3 square kernel, and a stride of 1.
        self.conv2 = nn.Conv2d(15, 30, 3, 1)
        # Dropout is performed twice in the network,
        # with the first time set to 0.25 and the
        # second time set to 0.5.
        self.dropout1 = nn.Dropout2d(0.25)
        self.dropout2 = nn.Dropout2d(0.5)
        # Two fully connected layers. Input is 2347380 because 243x161x60
        # as shown in the forward part.
        self.fc1 = nn.Linear(290400, 128)
        # Second fully connected layer has 128 inputs and 2 outputs for x and y values
        self.fc2 = nn.Linear(128, 2)

    # Define the structure for forward propagation.
    def forward(self, x):
        # Input dimensions: 490x326x3
        # Output dimensions: 488x324x15
        x = self.conv1(x)
        # Input dimensions: 488x324x15
        # Output dimensions: 244x162x15
        x = F.max_pool2d(x, 2)
        # Input dimensions: 244x162x15
        # Output dimensions: 242x160x15
        x = self.conv2(x)
        # Input dimensions: 242x160x30
        # Output dimensions: 121x80x30
        x = F.max_pool2d(x, 2)
        x = self.dropout1(x)
        # Input dimensions: 121x80x30
        # Output dimensions: 290400x1
        x = torch.flatten(x, 1)
        # Input dimensions: 290400x1
        # Output dimensions: 128x1
        x = self.fc1(x)
        x = F.relu(x)
        x = self.dropout2(x)
        # Input dimensions: 128x1
        # Output dimensions: 2x1
        output = self.fc2(x)
        return output


def train(args, model, device, train_loader, optimizer, epoch):
    # Specify that we are in training phase
    model.train()
    # Iterate through all minibatches.
    for batch_idx, batch_sample in enumerate(train_loader):
        # Send training data and the training labels to GPU/CPU
        data, target = batch_sample["image"].to(device, dtype=torch.float32), batch_sample["label"].to(device, dtype=torch.float32)
        # Zero the gradients carried over from previous step
        optimizer.zero_grad()
        # Obtain the predictions from forward propagation
        output = model(data)
        # Compute the mean squared error for loss
        loss = F.mse_loss(output, target)
        # Perform backward propagation to compute the negative gradient, and
        # update the gradients with optimizer.step()
        loss.backward()
        optimizer.step()
        # Send output to log if logging is needed
        if batch_idx % args.log_interval == 0:
            print('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                epoch, batch_idx * len(data), len(train_loader.dataset),
                100. * batch_idx / len(train_loader), loss.item()))


def test(args, model, device, test_loader):
    # Specify that we are in evaluation phase
    model.eval()
    # Set the loss initially to 0.
    test_loss = 0
    # No gradient calculation because we are in testing phase.
    with torch.no_grad():
        # For each testing example, we run forward
        # propagation to calculate the
        # testing prediction. Update the total loss
        # and the number of correct predictions
        # with the counters from above.
        for batch_idx, batch_sample in enumerate(test_loader):
            # Send training data and the training labels to GPU/CPU
            data, target = batch_sample["image"].to(device, dtype=torch.float32), batch_sample["label"].to(device,
                                                                                                           dtype=torch.float32)
            output = model(data)
            test_loss += F.mse_loss(output, target).item()

    # Average the loss by dividing by the total number of testing instances.
    test_loss /= len(test_loader.dataset)

    # Print out the statistics for the testing set.
    print('\nTest set: Average loss: {:.4f}\n'.format(
        test_loss))


def main():
    # Command line arguments for hyperparameters of
    # training and testing batch size, the number of
    # epochs, the learning rate, gamma, and other
    # settings such as whether to use a GPU device, the
    # random seed, how often to log, and
    # whether we should save the model.
    parser = argparse.ArgumentParser(description='PyTorch Object Detection')
    parser.add_argument('--batch-size', type=int, default=8, metavar='N',
                        help='input batch size for training (default: 8)')
    parser.add_argument('--test-batch-size', type=int, default=1000, metavar='N',
                        help='input batch size for testing (default: 1000)')
    parser.add_argument('--epochs', type=int, default=14, metavar='N',
                        help='number of epochs to train (default: 14)')
    parser.add_argument('--lr', type=float, default=1.0, metavar='LR',
                        help='learning rate (default: 1.0)')
    parser.add_argument('--gamma', type=float, default=0.7, metavar='M',
                        help='Learning rate step gamma (default: 0.7)')
    parser.add_argument('--no-cuda', action='store_true', default=False,
                        help='disables CUDA training')
    parser.add_argument('--seed', type=int, default=1, metavar='S',
                        help='random seed (default: 1)')
    parser.add_argument('--log-interval', type=int, default=10, metavar='N',
                        help='how many batches to wait before logging training status')

    parser.add_argument('--save-model', action='store_true', default=True,
                        help='For Saving the current Model')
    args = parser.parse_args()
    # Command to use gpu depending on command line arguments and if there is a cuda device
    use_cuda = not args.no_cuda and torch.cuda.is_available()

    # Random seed to use
    torch.manual_seed(args.seed)

    # Set to either use gpu or cpu
    device = torch.device("cuda" if use_cuda else "cpu")

    # GPU keywords.
    kwargs = {'num_workers': 1, 'pin_memory': True} if use_cuda else {}
    # Load in the training and testing datasets. Convert to pytorch tensor.
    train_data = DetectionImages(csv_file="../data/labels/train_labels.txt", root_dir="../data/train", transform=ToTensor())
    train_loader = DataLoader(train_data, batch_size=args.batch_size, shuffle=True, num_workers=0)
    test_data = DetectionImages(csv_file="../data/labels/validation_labels.txt", root_dir="../data/validation", transform=ToTensor())
    test_loader = DataLoader(test_data, batch_size=args.test_batch_size, shuffle=True, num_workers=0)

    # Run model on GPU if available
    model = Net().to(device)
    # Specify Adadelta optimizer
    optimizer = optim.Adadelta(model.parameters(), lr=args.lr)

    # Run for the set number of epochs. For each epoch, run the training
    # and the testing steps. Scheduler is used to specify the learning rate.
    scheduler = StepLR(optimizer, step_size=1, gamma=args.gamma)
    for epoch in range(1, args.epochs + 1):
        train(args, model, device, train_loader, optimizer, epoch)
        test(args, model, device, test_loader)
        scheduler.step()

    # Save model if specified by the command line argument
    if args.save_model:
        torch.save(model.state_dict(), "architecture1.pt")


if __name__ == '__main__':
    main()