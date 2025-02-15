import torch
import logging
from torchtext.data.datasets_utils import _check_default_set
from torchtext.data.datasets_utils import _wrap_datasets
from torchtext import datasets as raw
from torchtext.vocab import build_vocab_from_iterator
from torchtext.experimental.functional import (
    vocab_func,
    totensor,
    sequential_transforms,
)

logger_ = logging.getLogger(__name__)


def build_vocab(data):
    total_columns = len(data[0])
    data_list = [[] for _ in range(total_columns)]
    vocabs = []

    for line in data:
        for idx, col in enumerate(line):
            data_list[idx].append(col)
    for it in data_list:
        vocab = build_vocab_from_iterator(it, specials=['<unk>', '<pad>'])
        vocab.set_default_index(vocab['<unk>'])
        vocabs.append(vocab)

    return vocabs


def _setup_datasets(dataset_name, root, vocabs, split_):
    split = _check_default_set(split_, ('train', 'valid', 'test'), dataset_name)
    raw_iter_tuple = raw.DATASETS[dataset_name](root=root, split=split)
    raw_data = {}
    for name, raw_iter in zip(split, raw_iter_tuple):
        raw_data[name] = list(raw_iter)

    if vocabs is None:
        if "train" not in split:
            raise TypeError("Must pass a vocab if train is not selected.")
        logger_.info('Building Vocab based on train data')
        vocabs = build_vocab(raw_data["train"])
    else:
        if not isinstance(vocabs, list):
            raise TypeError("vocabs must be an instance of list")

        # Find data that's not None
        notnone_data = None
        for key in raw_data.keys():
            if raw_data[key] is not None:
                notnone_data = raw_data[key]
                break
        if len(vocabs) != len(notnone_data[0]):
            raise ValueError(
                "Number of vocabs must match the number of columns "
                "in the data")

    transformers = [
        sequential_transforms(vocab_func(vocabs[idx]),
                              totensor(dtype=torch.long))
        for idx in range(len(vocabs))
    ]
    logger_.info('Building datasets for {}'.format(split))
    return _wrap_datasets(tuple(SequenceTaggingDataset(raw_data[item], vocabs, transformers) for item in split), split_)


class SequenceTaggingDataset(torch.utils.data.Dataset):
    """Defines an abstraction for raw text sequence tagging iterable datasets.

    Currently, we only support the following datasets:

        - UDPOS
        - CoNLL2000Chunking
    """

    def __init__(self, data, vocabs, transforms):
        """Initiate sequence tagging dataset.

        Args:
            data: a list of word and its respective tags. Example:
                [[word, POS, dep_parsing label, ...]]
            vocabs: a list of vocabularies for its respective tags.
                The number of vocabs must be the same as the number of columns
                found in the data.
            transforms: a list of string transforms for words and tags.
                The number of transforms must be the same as the number of columns
                found in the data.
        """

        super(SequenceTaggingDataset, self).__init__()
        self.data = data
        self.vocabs = vocabs
        self.transforms = transforms

        if len(self.data[0]) != len(self.vocabs):
            raise ValueError("vocabs must have the same number of columns "
                             "as the data")

    def __getitem__(self, i):
        curr_data = self.data[i]
        if len(curr_data) != len(self.transforms):
            raise ValueError("data must have the same number of columns "
                             "with transforms function")
        return [self.transforms[idx](curr_data[idx]) for idx in range(len(self.transforms))]

    def __len__(self):
        return len(self.data)

    def get_vocabs(self):
        return self.vocabs


def UDPOS(root=".data", vocabs=None, split=("train", "valid", "test")):
    """ Universal Dependencies English Web Treebank

    Separately returns the training, validation, and test dataset

    Args:
        root: Directory where the datasets are saved. Default: ".data"
        vocabs: A list of voabularies for each columns in the dataset. Must be in an
            instance of List
            Default: None
        split: a string or tuple for the returned datasets
            (Default: ('train', 'valid', 'test'))
            By default, all the three datasets (train, test, valid) are generated. Users
            could also choose any one or two of them, for example ('train', 'test') or
            just a string 'train'. If 'train' is not in the tuple or string, a vocab
            object should be provided which will be used to process valid and/or test
            data.

    Examples:
        >>> from torchtext.datasets.raw import UDPOS
        >>> train_dataset, valid_dataset, test_dataset = UDPOS()
    """

    return _setup_datasets("UDPOS", root, vocabs, split)


def CoNLL2000Chunking(root=".data", vocabs=None, split=("train", "test")):
    """ CoNLL 2000 Chunking Dataset

    Separately returns the training and test dataset

    Args:
        root: Directory where the datasets are saved. Default: ".data"
        vocabs: A list of voabularies for each columns in the dataset. Must be in an
            instance of List
            Default: None
        split: a string or tuple for the returned datasets
            (Default: ('train', 'test'))
            By default, both datasets (train, test) are generated. Users
            could also choose any one or two of them, for example ('train', 'test') or
            just a string 'train'. If 'train' is not in the tuple or string, a vocab
            object should be provided which will be used to process valid and/or test
            data.

    Examples:
        >>> from torchtext.datasets.raw import CoNLL2000Chunking
        >>> train_dataset, test_dataset = CoNLL2000Chunking()
    """

    return _setup_datasets("CoNLL2000Chunking", root, vocabs, split)


DATASETS = {"UDPOS": UDPOS, "CoNLL2000Chunking": CoNLL2000Chunking}
