import os
import random

import numpy as np
import torch

RANDOM_SEED = 12345
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)
torch.manual_seed(RANDOM_SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(RANDOM_SEED)


class DataGenerator(object):
    def __init__(self, data_path, collection, split):
        super(DataGenerator, self).__init__()
        self.collection = collection
        if 'mb' in collection:
            self.fa = open(os.path.join(data_path, '{}/{}/a.toks'.format(collection, split)))
            self.fb = open(os.path.join(data_path, '{}/{}/b.toks'.format(collection, split)))
            self.fsim = open(os.path.join(data_path, '{}/{}/sim.txt'.format(collection, split)))
            self.fid = open(os.path.join(data_path, '{}/{}/id.txt'.format(collection, split)))
        elif 'qa' in collection:
            self.f = open(os.path.join(data_path, '{}/{}.csv'.format(collection, split)))
            # self.f.readline()  # skip headline
        else:
            self.f = open(os.path.join(data_path, 'datasets', '{}.csv'.format(collection)))

    def get_instance(self):
        if self.collection == 'mb':
            for a, b, sim, ID in zip(self.fa, self.fb, self.fsim, self.fid):
                return sim.replace('\n', ''), a.replace('\n', ''), \
                       b.replace('\n', ''), ID.replace('\n', '')
            return None, None, None, None
        elif self.collection == 'qa':
            for l in self.f:
                return l.replace('\n', '').split('\t')  # sim, qid, docid, a, b
            return None, None, None, None, None  
        else:
            for l in self.f:
                return l.replace('\n', '').split('\t')
            return None, None, None, None, None, None, None, None


def load_data(data_path, collection, batch_size, tokenizer, split='train', device='cuda'):
    test_batch, testqid_batch, mask_batch, label_batch, qid_batch, docid_batch = [], [], [], [], [], []
    data_set = []
    while True:
        dataGenerator = DataGenerator(data_path, collection, split)
        while True:
            if collection == 'mb':
                label, a, b, ID = dataGenerator.get_instance()
                qid, _, docid, _, _, _ = ID.split()
                qid = int(qid)
                docid = int(docid)

            elif collection == 'qa':
                label, qid, docid, a, b = dataGenerator.get_instance()
                # qid = float(qid)  # trec qid is in the format of '1.3'
                # docid = int(qid)
            
            else:
                raise ValueError('Invalid collection: {}'.format(collection))

            if label is None:
                break

            a = '[CLS] ' + a + ' [SEP]'
            b = b + ' [SEP]'

            a_index = tokenize_index(a, tokenizer)
            b_index = tokenize_index(b, tokenizer)

            combine_index = a_index + b_index
            segments_ids = [0] * len(a_index) + [1] * len(b_index)

            test_batch.append(torch.tensor(combine_index))
            testqid_batch.append(torch.tensor(segments_ids))
            mask_batch.append(torch.ones(len(combine_index)))
            label_batch.append(int(label))
            
            qid_batch.append(qid)
            docid_batch.append(docid)
            
            if len(test_batch) >= batch_size:
                # Convert inputs to PyTorch tensors
                tokens_tensor = torch.nn.utils.rnn.pad_sequence(test_batch, batch_first=True, padding_value=0).to(device)
                segments_tensor = torch.nn.utils.rnn.pad_sequence(testqid_batch, batch_first=True, padding_value=0).to(device)
                mask_tensor = torch.nn.utils.rnn.pad_sequence(mask_batch, batch_first=True, padding_value=0).to(device)
                label_tensor = torch.tensor(label_batch, device=device)
                # qid_tensor = torch.tensor(qid_batch, device=device)
                # docid_tensor = torch.tensor(docid_batch, device=device)
                # data_set.append((tokens_tensor, segments_tensor, mask_tensor, label_tensor, qid_tensor, docid_tensor)
                
                batch = (tokens_tensor, segments_tensor, mask_tensor, label_tensor, qid_batch, docid_batch)
                test_batch, testqid_batch, mask_batch, label_batch, qid_batch, docid_batch = [], [], [], [], [], []
                # yield (tokens_tensor, segments_tensor, mask_tensor, label_tensor, qid_tensor, docid_tensor)
                yield batch

        if len(test_batch) != 0:
            # Convert inputs to PyTorch tensors
            tokens_tensor = torch.nn.utils.rnn.pad_sequence(test_batch, batch_first=True, padding_value=0).to(device)
            segments_tensor = torch.nn.utils.rnn.pad_sequence(testqid_batch, batch_first=True, padding_value=0).to(device)
            mask_tensor = torch.nn.utils.rnn.pad_sequence(mask_batch, batch_first=True, padding_value=0).to(device)
            label_tensor = torch.tensor(label_batch, device=device)
            # qid_tensor = torch.tensor(qid_batch, device=device)
            # docid_tensor = torch.tensor(docid_batch, device=device)
            # data_set.append((tokens_tensor, segments_tensor, mask_tensor, label_tensor, qid_tensor, docid_tensor))
            
            batch = (tokens_tensor, segments_tensor, mask_tensor, label_tensor, qid_batch, docid_batch)
            test_batch, testqid_batch, mask_batch, label_batch, qid_batch, docid_batch = [], [], [], [], [], []  # docqid_batch -> docid_batch
            # yield (tokens_tensor, segments_tensor, mask_tensor, label_tensor, qid_tensor, docid_tensor)
            yield batch

        yield None

    return None


def load_trec_data(data_path, collection, batch_size, tokenizer, split='test', device='cpu'):
    test_batch, testqid_batch, mask_batch, label_batch, qid_batch, docid_batch = [], [], [], [], [], []
    data_set = []
    while True:
        dataGenerator = DataGenerator(data_path, collection, split)
        while True:
            label, sim, a, b, qno, docno, qidx, didx = dataGenerator.get_instance()
            if label is None:
                break

            a = '[CLS] ' + a + ' [SEP]'
            b = b + ' [SEP]'
            a_index = tokenize_index(a, tokenizer)
            b_index = tokenize_index(b, tokenizer)

            combine_index = a_index + b_index
            segments_ids = [0] * len(a_index) + [1] * len(b_index)
            ##
            combine_index = combine_index[:512]
            segments_ids = segments_ids[:512]
            ##

            test_batch.append(torch.tensor(combine_index))
            testqid_batch.append(torch.tensor(segments_ids))
            mask_batch.append(torch.ones(len(combine_index)))
            label_batch.append(int(label))
            qid = int(qidx)
            docid = int(didx)
            qid_batch.append(qid)
            docid_batch.append(docid)
            if len(test_batch) >= batch_size:
                # Convert inputs to PyTorch tensors
                tokens_tensor = torch.nn.utils.rnn.pad_sequence(test_batch, batch_first=True, padding_value=0).to(device)
                segments_tensor = torch.nn.utils.rnn.pad_sequence(testqid_batch, batch_first=True, padding_value=0).to(device)
                mask_tensor = torch.nn.utils.rnn.pad_sequence(mask_batch, batch_first=True, padding_value=0).to(device)
                label_tensor = torch.tensor(label_batch, device=device)
                qid_tensor = torch.tensor(qid_batch, device=device)
                docid_tensor = torch.tensor(docid_batch, device=device)
                data_set.append((tokens_tensor, segments_tensor, mask_tensor, label_tensor, qid_tensor, docid_tensor))
                test_batch, testqid_batch, mask_batch, label_batch, qid_batch, docid_batch = [], [], [], [], [], []
                yield (tokens_tensor, segments_tensor, mask_tensor, label_tensor, qid_tensor, docid_tensor)

        if len(test_batch) != 0:
            # Convert inputs to PyTorch tensors
            tokens_tensor = torch.nn.utils.rnn.pad_sequence(test_batch, batch_first=True, padding_value=0).to(device)
            segments_tensor = torch.nn.utils.rnn.pad_sequence(testqid_batch, batch_first=True, padding_value=0).to(device)
            mask_tensor = torch.nn.utils.rnn.pad_sequence(mask_batch, batch_first=True, padding_value=0).to(device)
            label_tensor = torch.tensor(label_batch, device=device)
            qid_tensor = torch.tensor(qid_batch, device=device)
            docid_tensor = torch.tensor(docid_batch, device=device)
            data_set.append((tokens_tensor, segments_tensor, mask_tensor, label_tensor, qid_tensor, docid_tensor))
            test_batch, testqid_batch, mask_batch, label_batch, qid_batch, docqid_batch = [], [], [], [], [], []
            yield (tokens_tensor, segments_tensor, mask_tensor, label_tensor, qid_tensor, docid_tensor)

        yield None

    return None


def tokenize_index(text, tokenizer):
    tokenized_text = tokenizer.tokenize(text)
    # Convert token to vocabulary indices
    tokenized_text = tokenized_text[:512]
    indexed_tokens = tokenizer.convert_tokens_to_ids(tokenized_text)
    return indexed_tokens
