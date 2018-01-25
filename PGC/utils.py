
from __future__ import unicode_literals, print_function, division

import time
import torch
import torch.nn as nn
from torch.autograd import Variable
import sys


def zero_pad(tokens, len_limit):
    if len(tokens) < len_limit: return tokens + [0] * (len_limit - len(tokens))
    else: return tokens[:len_limit]


def print_attention_dist(text_pair, vocab, att_dist):
    attentions = []
    for i in range(min(len(att_dist), len(text_pair.full_source_tokens))):
        word_idx = text_pair.full_source_tokens[i]
        if att_dist[i] > 0.05:
            if word_idx < len(vocab.index2word) : attentions.append((vocab.index2word[word_idx], att_dist[i]))
            else:
                for w in text_pair.unknown_tokens.keys():
                    if text_pair.unknown_tokens[w] == word_idx:
                        attentions.append((w, att_dist[i]))
                        break

        '''
        sample = 6
        pred = p_final.max(1)[1][sample].data[0]
        true = full_target_variable.narrow(1, token_i, 1).squeeze(-1)[sample].data[0]
        index2word = dataset.vocab.index2word
        if pred in index2word: pred_w = index2word[pred]
        else: pred_w = 'UNK'
        if true in index2word: true_w = index2word[true]
        else: true_w = 'UNK'
        print(print_attention_dist(samples[sample], dataset.vocab, token_input_dist[0].data))
        print(pred_w, true_w)
        '''

    return attentions


def get_batch_variables(samples, input_length, target_length, use_cuda, SOS_token):

    input_variable = Variable(torch.LongTensor([zero_pad(pair.masked_source_tokens, input_length) for pair in samples]))
    full_input_variable = Variable(torch.LongTensor([zero_pad(pair.full_source_tokens, input_length) for pair in samples]))
    target_variable = Variable(torch.LongTensor([zero_pad(pair.masked_target_tokens, target_length) for pair in samples]))
    full_target_variable = Variable(torch.LongTensor([zero_pad(pair.full_target_tokens, target_length) for pair in samples]))
    decoder_input = Variable(torch.LongTensor([[SOS_token] for i in range(len(samples))]))

    if use_cuda:
        return input_variable.cuda(), full_input_variable.cuda(), target_variable.cuda(), \
               full_target_variable.cuda(), decoder_input.cuda()
    else:
        return input_variable, full_input_variable, target_variable, full_target_variable, decoder_input


def progress_bar(fraction, e):
    sys.stdout.write('\r')
    sys.stdout.write("[%-60s] %d%%" % ('='*int((60*(e+1)/10)), (100*(e+1)/10)))
    sys.stdout.flush()
    sys.stdout.write(", epoch %d" % (e+1))
    sys.stdout.flush()


def translate_word(token, text_pair, vocab):
    if token in vocab.index2word: return vocab.index2word[token]
    if token in text_pair.unknown_tokens.values():
        return [k for k in text_pair.unknown_tokens if text_pair.unknown_tokens[k] == token][0]
    return 3


def predict_and_print(pair, encoder, decoder, input_length, target_length, SOS_token, vocab, use_cuda, UNK_token):
    print(pair.target_text)

    input_variable, full_input_variable, _, _, decoder_input = \
        get_batch_variables([pair], input_length, target_length, use_cuda, SOS_token)

    encoder_hidden = encoder.init_hidden(1, use_cuda)

    encoder_outputs, encoder_hidden = encoder(input_variable, encoder_hidden)
    decoder_hidden = torch.cat((encoder_hidden[0], encoder_hidden[1]), -1)

    result = []
    gen_sequence = []
    for token_i in range(target_length):

        decoder_hidden, p_final, p_gen, p_vocab, attention_dist = decoder(decoder_input, decoder_hidden, encoder_outputs, full_input_variable)
        '''
        p_word, decoded_word_idx = p_final.max(1)
        decoded_word = translate_word(decoded_word_idx.data[0], pair, dataset.vocab)
        p_att, attended_pos = attention_dist.max(1)
        attended_word = translate_word(pair.full_source_tokens[attended_pos.data[0]], pair, dataset.vocab)

        if decoded_word_idx.data[0] < 25000: decoder_input = Variable(torch.LongTensor([[decoded_word_idx.data[0]]]))
        else: decoder_input = Variable(torch.LongTensor([[UNK_token]]))
        if use_cuda: decoder_input = decoder_input.cuda()

        result.append({'p_gen': round(p_gen.data[0][0], 3),'word': decoded_word, 'p_word': round(p_word.data[0], 3),
                      'att_word': attended_word, 'p_att': round(p_att.data[0], 3)})
        '''
        p_vocab_word, vocab_word_idx = p_vocab.max(1)

        gen_sequence.append((translate_word(vocab_word_idx.data[0], pair, vocab), round(p_vocab_word.data[0], 3)))

    return result, gen_sequence

#predict_and_print(training_pairs[20])