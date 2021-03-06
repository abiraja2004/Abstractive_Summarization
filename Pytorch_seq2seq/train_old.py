from __future__ import unicode_literals, print_function, division

import time
import torch
import torch.nn as nn
from torch.autograd import Variable
from torch import optim
import torch.nn.functional as F
import pickle

#from PGC.model import EncoderRNN, AttnDecoderRNN
import PGC.utils as utils

use_cuda = True#torch.cuda.is_available()
multi_gpu = False
#from Pytorch_seq2seq.data_loader import *
data_path = '/home/havikbot/MasterThesis/Data/CNN_dailyMail/DailyMail/model_datasets/'
path_2 = '/home/shomea/h/havikbot/MasterThesis/'

with open(path_2 +'DM_25k_summary.pickle', 'rb') as f: dataset = pickle.load(f)

SOS_token = 1
EOS_token = 2
UNK_token = 3

batch_size = 32
embedding_size = 128
hidden_size = 256
input_length = 300
target_length = 40
learning_rate= 0.015
teacher_forcing_ratio = 0.5

vocab_size = len(dataset.vocab.index2word)
training_pairs = dataset.summary_pairs[0:int(len(dataset.summary_pairs)*0.8)]
test_pairs = dataset.summary_pairs[int(len(dataset.summary_pairs)*0.8):]

encoder = EncoderRNN(vocab_size, hidden_size=embedding_size)
emb_w = encoder.embedding.weight # use weight sharing?
decoder = AttnDecoderRNN(hidden_size, embedding_size, vocab_size, 1, dropout_p=0.1, embedding_weight=None)


if use_cuda:
    encoder.cuda()
    decoder.cuda()

encoder_optimizer = optim.Adagrad(encoder.parameters(), lr= learning_rate, weight_decay=0.0000001)# lr=learning_rate)
decoder_optimizer = optim.Adagrad(decoder.parameters(), lr= learning_rate, weight_decay=0.0000001)
criterion = nn.NLLLoss()


def train_batch(samples, encoder, decoder, input_length, target_length, use_cuda):
    start = time.time()
    input_variable, full_input_variable, target_variable, full_target_variable, decoder_input = \
        get_batch_variables(samples, input_length, target_length, use_cuda, SOS_token)

    encoder_hidden = encoder.init_hidden(len(samples), use_cuda)
    encoder_optimizer.zero_grad()
    decoder_optimizer.zero_grad()
    loss = 0

    encoder_outputs, encoder_hidden = encoder(input_variable, encoder_hidden)
    decoder_hidden = torch.cat((encoder_hidden[0], encoder_hidden[1]), -1)

    for token_i in range(target_length):

        decoder_hidden, p_final, p_gen, p_vocab, attention_dist = \
            decoder(decoder_input, decoder_hidden, encoder_outputs, full_input_variable, use_cuda)

        loss += criterion(torch.log(p_final.clamp(min=1e-8)), full_target_variable.narrow(1, token_i, 1).squeeze(-1))
        decoder_input = target_variable.narrow(1, token_i, 1) # Teacher forcing

    loss.backward()
    encoder_optimizer.step()
    decoder_optimizer.step()

    return loss.data[0] / target_length, time.time() - start


def predict(samples, encoder, decoder, input_length, target_length, use_cuda, beam_width, vocab):
    input_variable, full_input_variable, target_variable, full_target_variable, decoder_input = \
        get_batch_variables(samples, input_length, target_length, use_cuda, SOS_token)
    encoder_hidden = encoder.init_hidden(len(samples), use_cuda)

    encoder_outputs, encoder_hidden = encoder(input_variable, encoder_hidden)
    decoder_hidden = torch.cat((encoder_hidden[0], encoder_hidden[1]), -1)

    result = []
    for token_i in range(target_length):

        decoder_hidden, p_final, p_gen, p_vocab, attention_dist = \
            decoder(decoder_input, decoder_hidden, encoder_outputs, full_input_variable, use_cuda)

        if not beam_width:
            p_vocab_word, vocab_word_idx = p_final.max(1)
            result.append([{'token_idx': vocab_word_idx.data[i],
                            'word': translate_word(vocab_word_idx.data[i], samples[i], vocab),
                            'p_gen': round(p_gen.data[i][0], 3)}
                                for i in range(len(samples))])
            print(decoder_input)
            decoder_input = torch.unsqueeze(vocab_word_idx, 1)

            #decoder_input = target_variable.narrow(1, token_i, 1) # Teacher forcing
        else:
            pass
            # conduct beam search
    return result

def train_model(nb_epochs, encoder):
    for e in range(nb_epochs):
        epoch_loss = 0
        epoch_time = 0
        for b in range(int(len(training_pairs)/batch_size)):
            batch = training_pairs[b*batch_size:(b+1)*batch_size]
            loss, time_ = train_batch(batch, encoder, decoder, input_length, target_length, use_cuda)
            epoch_loss += loss
            epoch_time += time_
            if b % 20 == 0:
                print(b*batch_size, '/', len(training_pairs), "loss:", epoch_loss/ (b+1), 'time:', epoch_time/(b+1) )
                sample = b*batch_size
                result = predict([training_pairs[sample]], encoder, decoder, input_length, target_length, use_cuda, False, dataset.vocab)
                print(training_pairs[sample].target_text)
                print(" ".join([t[0]['word'] +"(" + str(t[0]['p_gen']) + ")" for t in result]))
                print()

train_model(30, encoder)

