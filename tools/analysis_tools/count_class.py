# Copyright (c) OpenMMLab. All rights reserved.
import argparse
import os.path as osp

import matplotlib.pyplot as plt
import mmcv
import numpy as np
import seaborn as sns
from mmcv import Config

from mmselfsup.datasets import build_dataset


def plot_class_dist(labels,
                    percentage,
                    save_dir,
                    logger,
                    title=None,
                    figsize=[40, 40],
                    ylim=(None, None)):
    labels[labels == 0] = 1e-4
    sns.set(style='whitegrid', font_scale=3, context='paper')
    figsize = [25.4, 57.2]
    plt.rcParams['figure.figsize'] = figsize
    plt.rcParams['figure.autolayout'] = True
    my_pal = [
        '#e60049', '#0bb4ff', '#50e991', '#e6d800', '#9b19f5', '#ffa300',
        '#dc0ab4', '#b3d4ff', '#00bfa0'
    ]
    num_unique_labels = len(labels)
    pal = sns.color_palette(my_pal, n_colors=num_unique_labels)

    ax = sns.barplot(  # noqa F841
        y=list(map(str, np.arange(num_unique_labels))),
        x=labels,
        palette=pal,
        ci=None,
    )
    # ax.bar_label(ax.containers[0]) # annotate the bars
    plt.gca().axes.get_xaxis().set_visible(False)
    plt.gca().axes.get_yaxis().set_visible(False)
    plt.ylim(ylim)
    plt.savefig(
        osp.join(save_dir, f'p-0.{percentage}_distribution_histogram.png'))
    plt.clf()
    plt.cla()
    plt.close('all')


def parse_args():
    parser = argparse.ArgumentParser(
        description='select samples with uniformity and cartography metrics')
    parser.add_argument('config', help='train config file path')
    parser.add_argument(
        '--work_dir', type=str, default=None, help='the dir to save results')
    parser.add_argument(
        '--idx_dir', type=str, default=None, help='the dir to load idx files')
    parser.add_argument(
        '--random_out_dir',
        type=str,
        default=None,
        help='the dir to load random .out files')
    parser.add_argument(
        '--dataset_config',
        default='configs/benchmarks/classification/tsne_pathmnist.py',
        help='extract dataset config file path')
    parser.add_argument(
        '--method',
        choices=['random', 'active'],
        default='active',
        help='plot class count for active querying methods.')
    parser.add_argument('--seed', type=int, default=0, help='random seed')

    args = parser.parse_args()
    return args


def convert_array_to_cnt_array(ori_labels, num_classes):
    unique, counts = np.unique(ori_labels, return_counts=True)
    count_dict = dict(zip(unique, counts))
    labels = np.zeros(num_classes)
    for _class in count_dict.keys():
        labels[_class] = count_dict[_class]
    return labels


def main():
    args = parse_args()
    # get pseudo labels
    cfg = Config.fromfile(args.config)
    if args.work_dir is not None:
        # update configs according to CLI args if args.work_dir is not None
        work_type = args.config.split('/')[1]
        cfg.work_dir = args.work_dir
    elif cfg.get('work_dir', None) is None:
        # use config filename as default work_dir if cfg.work_dir is None
        work_type = args.config.split('/')[1]
        cfg.work_dir = osp.join('./work_dirs', work_type,
                                osp.splitext(osp.basename(args.config))[0],
                                'data_selection')
    mmcv.mkdir_or_exist(cfg.work_dir)
    dataset_cfg = mmcv.Config.fromfile(args.dataset_config)
    dataset = build_dataset(dataset_cfg.data.extract)
    gt_labels = dataset.data_source.get_gt_labels()
    unique, counts = np.unique(gt_labels, return_counts=True)
    num_real_classes = len(unique)

    # define percentage list
    dataset_name = dataset_cfg.name.split('_')[0]
    if dataset_name in ['pathmnist']:
        plist = [i for i in range(15, 100, 5)] + \
            [i for i in range(100, 1000, 50)] + \
            [i for i in range(1000, 10000, 500)] + \
            [i for i in range(10000, 100000, 5000)]
    elif dataset_name in [
            'organamnist', 'pneumoniamnist', 'bloodmnist', 'dermamnist'
    ]:
        plist = [i for i in range(100, 1000, 100)] + \
            [i for i in range(1000, 10000, 1000)] + \
            [i for i in range(10000, 100000, 10000)]
    elif dataset_name in ['tissuemnist', 'octmnist']:
        plist = [i for i in range(10, 100, 10)] + \
            [i for i in range(100, 1000, 100)] + \
            [i for i in range(1000, 10000, 1000)] + \
            [i for i in range(10000, 100000, 10000)]
    elif dataset_name in ['breastmnist', 'retinamnist']:
        plist = [i for i in range(500, 10000, 500)] + \
            [i for i in range(10000, 100000, 5000)]

    num_train = len(dataset)
    zfill = 5
    p = [str(i).zfill(zfill) for i in plist]
    num_select_list = [int(num_train * i / 100000.0) for i in plist]

    if args.method == 'active':
        flag_list = [
            'consistency', 'vaal', 'margin', 'uncertainty', 'coreset', 'bald',
            'hard'
        ]
        flag_list = [x + '_idx.npy' for x in flag_list]

        # load idx file
        for flag in flag_list:
            idx_total_list = np.load(
                osp.join(args.idx_dir, dataset_name, flag))
            for pos, num_select in enumerate(num_select_list):
                idx_sub_list = idx_total_list[:num_select]
                selected_labels = gt_labels[idx_sub_list]
                unique, counts = np.unique(selected_labels, return_counts=True)
                num_slected_class = len(unique)
                selected_class_ratio = num_slected_class / num_real_classes
                print(flag, p[pos], num_select, selected_class_ratio)
    elif args.method == 'random':
        # plist = [15, 30]
        plist = [100, 200]  # blood, organa
        p = [str(i).zfill(zfill) for i in plist]
        num_select_list = [int(num_train * i / 100000.0) for i in plist]
        # load random .out file
        for p_i, percentage in enumerate(p):
            percentage_selected_class_ratio_list = []
            for run in [i + 1 for i in range(60)]:
                idx_sub_list = np.random.permutation(range(
                    len(gt_labels)))[:num_select_list[p_i]]
                selected_labels = gt_labels[idx_sub_list]
                unique, counts = np.unique(selected_labels, return_counts=True)
                num_slected_class = len(unique)
                selected_class_ratio = num_slected_class / num_real_classes
                percentage_selected_class_ratio_list.append(
                    selected_class_ratio)
            print(percentage, np.mean(percentage_selected_class_ratio_list),
                  np.std(percentage_selected_class_ratio_list))


if __name__ == '__main__':
    main()
