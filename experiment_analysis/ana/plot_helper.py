import matplotlib
import logging

matplotlib.rcParams["axes.labelcolor"] = "black"
matplotlib.rcParams["axes.edgecolor"] = "black"
matplotlib.rcParams["xtick.color"] = "black"
matplotlib.rcParams["ytick.color"] = "black"
matplotlib.rcParams["xtick.labelsize"] = 8
matplotlib.rcParams["ytick.labelsize"] = 8
matplotlib.rcParams["xtick.major.pad"] = 2  # padding between text and the tick
matplotlib.rcParams["ytick.major.pad"] = 2  # default 3.5
matplotlib.rcParams["lines.dash_capstyle"] = "butt"
matplotlib.rcParams["lines.solid_capstyle"] = "butt"
matplotlib.rcParams["font.size"] = 6
matplotlib.rcParams["mathtext.default"] = "regular"
matplotlib.rcParams["axes.titlesize"] = 9
matplotlib.rcParams["axes.labelsize"] = 9
matplotlib.rcParams["legend.fontsize"] = 6
matplotlib.rcParams["legend.facecolor"] = "#D4D4D4"
matplotlib.rcParams["legend.framealpha"] = 0.8
matplotlib.rcParams["legend.frameon"] = True
matplotlib.rcParams["axes.spines.right"] = False
matplotlib.rcParams["axes.spines.top"] = False
matplotlib.rcParams["figure.figsize"] = [3.4, 2.7]  # APS single column
matplotlib.rcParams["figure.dpi"] = 200
matplotlib.rcParams["savefig.facecolor"] = (0.9, 1.0, 1.0, 0.0)  # transparent figure bg
matplotlib.rcParams["axes.facecolor"] = (0.9, 1.0, 1.0, 0.0)

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import pandas as pd
import scipy.stats
from itertools import combinations
import arviz as az

from .utility import hierarchy_scores, structure_names, area_groups

log = logging.getLogger("plot_helper")

# ------------------------------------------------------------------------------ #
# lookup tables
# ------------------------------------------------------------------------------ #


color_palette = sns.color_palette()
structures_colors = {
    "V1": color_palette[4],
    "LM": color_palette[0],
    "RL": color_palette[9],
    "AL": color_palette[8],
    "PM": color_palette[1],
    "AM": color_palette[3],
    "LGN": color_palette[6],
    "LP": color_palette[2],
}

structure_colors = {
    "V1": "#9467BD",
    "LM": "#2078B4",
    "RL": "#1ABECF",
    "AL": "#BDBD21",
    "PM": "#FF7F0F",
    "AM": "#D62729",
    "LGN": "#F4C9E7",
    "LP": "#AAD9AB",
    "thalamus_grouped": "#999999",
    "V1_grouped": "#4C4C4C",
    "higher_grouped": "#4C4C4C",
}

y_labels = {
    "tau_double": "correlation\ntimescale " + r"$\it{\tau}_{\rm {c}}$ (ms)",
    "tau_single": "correlation\ntimescale " + r"$\it{\tau}_{\rm {c1}}$ (ms)",
    "R_tot": "predictability " + r"$\it{R}_{\rm {tot}}$",
    "tau_R": "information\ntimescale " + r"$\it{\tau}_{\rm {R}}$ (ms)",
}

y_labels_short = {
    "tau_double": r"$\it{\tau}_{\rm {c}}$ (ms)",
    "tau_single": r"$\it{\tau}_{\rm {c1}}$ (ms)",
    "R_tot": r"$\it{R}_{\rm {tot}}$",
    "tau_R": r"$\it{\tau}_{\rm {R}}$ (ms)",
}



# ------------------------------------------------------------------------------ #
# high level
# ------------------------------------------------------------------------------ #


def row_structure_groups(df, axes=None):

    if axes is None:
        fig, axes = plt.subplot_mosaic(
            [["tau_double", "tau_R", "R_tot"]],
            figsize=(16 / 2.54, 5 / 2.54),
        )
    else:
        fig = axes["tau_double"].get_figure()

    panel_areas_grouped(df, "tau_double", ax=axes["tau_double"])
    panel_areas_grouped(df, "tau_R", ax=axes["tau_R"])
    panel_areas_grouped(df, "R_tot", ax=axes["R_tot"])

    fig.tight_layout()

    return axes


def row_hierarchy_score(df, axes=None):

    if axes is None:
        fig, axes = plt.subplot_mosaic(
            [["tau_double", "tau_R", "R_tot"]],
            figsize=(16 / 2.54, 5 / 2.54),
        )
    else:
        fig = axes["tau_double"].get_figure()

    panel_hierarchy_score(df, "tau_double", ax=axes["tau_double"])
    panel_hierarchy_score(df, "tau_R", ax=axes["tau_R"])
    panel_hierarchy_score(df, "R_tot", ax=axes["R_tot"])

    fig.tight_layout()

    return axes


def panel_areas_grouped(df, obs, ax=None):

    assert obs in ["tau_double", "tau_single", "R_tot", "tau_R"]

    # we use a different naming convention, add a column for that
    if "structure_name" not in df.columns:
        df["structure_name"] = df["ecephys_structure_acronym"].apply(
            lambda x: structure_names[x]
        )

    if ax is None:
        fig, ax = plt.subplots(figsize=(4, 3))
    else:
        fig = ax.get_figure()

    stimuli = df["stimulus"].unique()
    blocks = df["block"].unique()
    log.info(f"grouped {obs} for {stimuli} {blocks} with {len(df)} rows")

    # ------------------------------------------------------------------------------ #
    # plot markers
    # ------------------------------------------------------------------------------ #

    for adx, area in enumerate(area_groups.keys()):
        df_area = df.query(f"structure_name in {area_groups[area]}")

        if "tau" in obs:
            # everything above 10s is unrealistic
            num_dropped = len(df_area.query(f"{obs} > 10"))
            log.debug(f"dropping {num_dropped} rows with too large timescales")
            df_area = df_area.query(f"{obs} <= 10")

        log.debug(f"{area} has {len(df_area)} rows")
        resampled_estimates = _pd_bootstrap(df_area, obs)
        median = df_area[obs].median()
        median_bs = np.median(resampled_estimates)
        quantiles = np.quantile(resampled_estimates, [0.025, 0.975])
        log.debug(
            f"{area} median_bs: {median_bs:.2f}, median: {median:.2f} quantiles:"
            f" {quantiles}"
        )

        # plot the area group
        left, center, right = _x_pos(area)
        ax.plot(
            [left, right],
            [median, median],
            color=structure_colors[area],
            linewidth=1.2,
            zorder=1,
            solid_capstyle="round",
        )
        ax.plot(
            [center, center],
            [quantiles[0], quantiles[1]],
            color=structure_colors[area],
            linewidth=1.2,
            zorder=1,
            solid_capstyle="round",
            clip_on=False,
        )
        ax.plot(
            center,
            median,
            "o",
            color=structure_colors[area],
            ms=2.0,
            zorder=2,
            clip_on=False,
        )

        # plot the individual strucutres
        for sdx, structure in enumerate(area_groups[area]):
            df_structure = df_area.query(f"structure_name == '{structure}'")
            resampled_estimates = _pd_bootstrap(df_structure, obs)
            median = df_structure[obs].median()
            median_bs = np.median(resampled_estimates)
            quantiles = np.quantile(resampled_estimates, [0.025, 0.975])

            ax.plot(
                [_x_pos(structure), _x_pos(structure)],
                [quantiles[0], quantiles[1]],
                color=structure_colors[structure],
                linewidth=1.6,
                zorder=1,
                clip_on=False,
            )
            ax.plot(
                _x_pos(structure),
                median,
                "o",
                color="white",
                mec=structure_colors[structure],
                mew=0.8,
                ms=5,
                zorder=2,
                clip_on=False,
            )

    # ------------------------------------------------------------------------------ #
    # p values
    # ------------------------------------------------------------------------------ #

    # comparing between i and j
    pairs = np.array(list(combinations(area_groups.keys(), 2)))
    for idx, (i, j) in enumerate(pairs[[1, 2, 0]]):
        dfi = df.query(f"structure_name in {area_groups[i]}")
        dfj = df.query(f"structure_name in {area_groups[j]}")

        MW_u, MW_p = scipy.stats.mannwhitneyu(
            dfi[obs], dfj[obs], alternative="two-sided"
        )
        log.debug(f"{idx} {i} vs. {j} MW_p: {MW_p:.3g}")

        if MW_p < 0.001:
            p_str = "***"
        elif MW_p < 0.01:
            p_str = "**"
        elif MW_p < 0.05:
            p_str = "*"
        else:
            p_str = "ns."

        # plot the p value bar, x in data coordinates, y in axis coordinates
        x1 = _x_pos(i)[2] - (_x_pos(i)[2] - _x_pos(i)[0]) / 2
        x2 = _x_pos(j)[2] - (_x_pos(j)[2] - _x_pos(j)[0]) / 2
        y_line = 0.95 - 0.07 * (idx + 1)
        y_text = 0.95 - 0.07 * (idx + 1) + 0.05

        ax.plot(
            [x1, x2],
            [y_line, y_line],
            color="black",
            linewidth=1,
            zorder=1,
            transform=ax.get_xaxis_transform(),
            clip_on=False,
        )

        ax.text(
            (x1 + x2) / 2,
            y_text,
            p_str,
            ha="center",
            va="top",
            fontsize=7,
            color="black",
            zorder=2,
            transform=ax.get_xaxis_transform(),
            clip_on=False,
        )

    # ------------------------------------------------------------------------------ #
    # axis styling
    # ------------------------------------------------------------------------------ #

    x_labels = {
        "thalamus": 0.4,
        "V1": 1.7,
        "higher\ncortical": 2.9,
    }

    ax.set_xticks(list(x_labels.values()))
    ax.set_xticklabels(list(x_labels.keys()))

    # remove x axis ticks and line
    ax.tick_params(axis="x", which="both", bottom=False, top=False, labelbottom=True)
    ax.tick_params(axis="y", which="both", left=False, right=False, labelleft=True)
    ax.spines["bottom"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["right"].set_visible(False)

    if "tau" in obs:
        # seconds to milliseconds
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: f"{x*1000:.0f}"))

    # y-limits, hard-coded
    if obs == "tau_double" or obs == "tau_single":
        ylim = (0.175, 0.6)
    elif obs == "tau_R":
        ylim = (0.01, 0.07)
    elif obs == "R_tot":
        ylim = (0.04, 0.09)
    else:
        ylim = (None, None)

    # add 1% add each end to avoid clipping the grid
    ax.set_ylim(
        ylim[0] - 0.01 * (ylim[1] - ylim[0]), ylim[1] + 0.01 * (ylim[1] - ylim[0])
    )

    # gray grid, in the background
    ax.grid(axis="y", color="0.9", linestyle="-", linewidth=1)
    ax.set_axisbelow(True)

    ax.set_ylabel(y_labels[obs])

    return ax


def panel_hierarchy_score(df, obs, ax=None, plot_option="default"):

    assert obs in ["tau_double", "tau_single", "R_tot", "tau_R"]

    # we use a different naming convention, add a column for that
    if "structure_name" not in df.columns:
        df["structure_name"] = df["ecephys_structure_acronym"].apply(
            lambda x: structure_names[x]
        )

    # check that all provided rows also have a hierarchy score
    assert np.all(s in hierarchy_scores.keys() for s in df["structure_name"].unique())
    if "LGN" in df["structure_name"].unique() or "LP" in df["structure_name"].unique():
        log.info("dropping LGN and LP to focus on cortical hierarchy")
        df = df.query("structure_name not in ['LGN', 'LP']")

    if ax is None:
        fig, ax = plt.subplots(figsize=(4, 3))
    else:
        fig = ax.get_figure()

    stimulti = df["stimulus"].unique()
    blocks = df["block"].unique()
    log.info(
        f"plotting {obs} agains hierarchy score for {stimulti} {blocks} with"
        f" {len(df)} rows"
    )

    if "tau" in obs:
        # everything above 10s is unrealistic
        num_dropped = len(df.query(f"{obs} > 10"))
        log.debug(f"dropping {num_dropped} rows with too large timescales")
        df = df.query(f"{obs} <= 10")

    # ------------------------------------------------------------------------------ #
    # plot markers
    # ------------------------------------------------------------------------------ #

    xs = []
    ys = []

    for sdx, structure in enumerate(df["structure_name"].unique()):

        df_strct = df.query(f"structure_name == '{structure}'")

        x = hierarchy_scores[structure]
        median = df_strct[obs].median()
        resampled_estimates = _pd_bootstrap(df_strct, obs)
        median_bs = np.median(resampled_estimates)
        quantiles = np.quantile(resampled_estimates, [0.025, 0.975])
        log.debug(
            f"{structure} median_bs: {median_bs:.2f}, median: {median:.2f} quantiles:"
            f" {quantiles}"
        )

        xs.append(x)
        ys.append(median)

        # markers
        ax.plot(
            x,
            median,
            "o",
            color="white",
            mec=structure_colors[structure],
            mew=0.8,
            ms=5,
            zorder=3,
            clip_on=True,
        )
        ax.plot(
            [x, x],
            [quantiles[0], quantiles[1]],
            color=structure_colors[structure],
            linewidth=1.6,
            zorder=2,
            clip_on=True,
        )

    # linear fit
    slope, intercept, r, p, std = scipy.stats.linregress(xs, ys)
    x_range = np.linspace(min(xs), max(xs), 10)

    ax.plot(
        x_range,
        x_range * slope + intercept,
        ls="--",
        color="black",
        alpha=0.5,
        linewidth=1.2,
        zorder=1,
        clip_on=False,
    )

    r_p, p_p = scipy.stats.pearsonr(xs, ys)
    r_s, p_s = scipy.stats.spearmanr(xs, ys)

    correlation_stats = {"pearson": [r_p, p_p], "spearman": [r_s, p_s]}

    if plot_option == "default":
        text = ""
        text += r"$\it{r}_{\rm P} = " + f"{r_p:.2f}" + r"$" + "  "
        text += r"$\it{P}_{\rm P} = " + f"{p_p:.2f}" + r"$" + "\n"
        text += r"$\it{r}_{\rm S} = " + f"{r_s:.2f}" + r"$" + "  "
        text += r"$\it{P}_{\rm S} = " + f"{p_s:.2f}" + r"$" + "\n"
        text_kwargs = dict(
            s=text,
            fontsize=6.5,
            color="black",
            transform=ax.transAxes,
        )
        # if "tau" in obs:
        ax.text(0.99, 0.015, ha="right", va="bottom", **text_kwargs)
        # else:
        # ax.text(0.25, 0.015, ha="left", va="bottom", **text_kwargs)
    # ------------------------------------------------------------------------------ #
    # axis styling
    # ------------------------------------------------------------------------------ #

    if "tau" in obs:
        # seconds to milliseconds
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: f"{x*1000:.0f}"))

    ax.xaxis.set_major_locator(plt.MultipleLocator(0.3))
    ax.xaxis.set_minor_locator(plt.MultipleLocator(0.1))

    ax.set_xlabel("hierarchy score")
    ax.set_ylabel(y_labels[obs])

    ax.tick_params(axis="y", which="both", left=False, right=False, labelleft=True)

    ax.spines["bottom"].set_visible(True)
    ax.spines["right"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ax.spines["left"].set_visible(False)

    # y-limits, hard-coded
    if obs == "tau_double" or obs == "tau_single":
        ylim = (0.15, 0.6)
    elif obs == "tau_R":
        ylim = (0.025, 0.07)
    elif obs == "R_tot":
        ylim = (0.06, 0.09)
    else:
        ylim = (None, None)

    # add 1% add each end to avoid clipping the grid
    ax.set_ylim(
        ylim[0] - 0.01 * (ylim[1] - ylim[0]), ylim[1] + 0.01 * (ylim[1] - ylim[0])
    )

    # grid
    ax.grid(axis="y", color="0.9", linestyle="-", linewidth=1)
    ax.set_axisbelow(True)

    # format x axis
    plt.minorticks_off()
    ax.set_xticks([-0.25, 0, 0.25])

    return ax, correlation_stats


def panel_stimulus_violins(df, xlabels=None, ax=None, logscale=False, plot_ylabel = True, areawise_plot=False, area_name=None, x_area_name=None, bonferroni_correction=None, **kwargs):
    """
    Create a single panel for the sensitivity. Query the dataframe beforehand to the right blocks / stimuli!

    This is a wrapper around fancy_violins() that does some more styling.
    """

    defaults = dict(
        category="stimulus",
        observable="R_tot",
        violin_kwargs=dict(
            scale="width",
        ),
        swarm_kwargs=dict(
            size=1.4,
        ),
        num_swarm_points=400,
        same_points_per_swarm=True,
        seed=44,
        replace=False,
        palette={
            "merged_3.0_and_8.0" : "#233954",
            "null" : "#EA5E48",
        },
    )

    # Update defaults with kwargs, overwriting existing keys
    defaults.update(kwargs)
    kwargs = defaults
    obs = kwargs["observable"]

    if "tau_" in obs:
        # seconds to ms
        df[obs] = df[obs] * 1000

    if logscale:
        # use a log-scale for the y-axis. datatransform before plotting,
        # and fix ticks afterwards.
        num_rows_before = len(df)
        log_values = np.log10(df[obs])
        #  pd.dropna does not drop inf/-inf, so we have to cast them.
        log_values = np.where(np.isinf(log_values), np.nan, log_values)
        df[f"log_{obs}"] = log_values
        kwargs["observable"] = f"log_{obs}"
        df = df.dropna(subset=[f"log_{obs}"])
        num_rows_after = len(df)
        log.info(f"dropped {num_rows_before - num_rows_after} rows with nan / inf")

    category = kwargs["category"]
    labels = df[category].unique()
    num_violins = len(labels)

    # only use units that occur in every condition
    valid_units = (
        df.groupby("unit_id")
        .filter(lambda x: len(x) == num_violins)["unit_id"]
        .unique()
    )
    df = df.query("unit_id in @valid_units")
    # sanity check:
    num_rows_per_label = len(df.query(f"{category} == '{labels[0]}'"))
    for l in labels:
        assert len(df.query(f"{category} == '{l}'")) == num_rows_per_label

    N = num_rows_per_label

    log.info(f"violins for {obs}, {labels}, N={N}")

    # p values and differences between labels:
    # if we use `kwargs['observable']` instead of obs, it would potentially be log-difference, but we want in lin-space because otherwise differences would are hard to interpret.
    pivot_df = df.pivot(index="unit_id", columns=category, values=obs)
    for i, j in combinations(range(0, len(labels)), 2):
        diff = pivot_df[labels[j]] - pivot_df[labels[i]]
        p = scipy.stats.wilcoxon(diff).pvalue

        # do we want median of pairwise differences
        diff_percent = (diff / pivot_df[labels[i]]) * 100
        diff_percent = np.median(diff_percent)

        # or difference of sample medians
        mi = np.median(pivot_df[labels[i]])
        mj = np.median(pivot_df[labels[j]])
        diff_median_percent = ((mj - mi) / mi) * 100

        log.info(f"median [{labels[i]}]: {mi:.3f}, [{labels[j]}]: {mj:.3f}")
        log.info(
            f"{labels[i]} vs {labels[j]} pairwise_diff={diff_percent:.1f}% diff_of_medians={diff_median_percent:.1f}% {p=}"
        )

    if areawise_plot:
        pos_text_x = 0.5
        pos_text_y = 1.05
        if p < 0.05 * bonferroni_correction:
            if p >= 1e-8:
                p_text = r"$\it{p}$ = " + _format_base_ten(p)
            else:
                p_text = r"$\it{p} < 10^{-8}$"

            ax.text(
                pos_text_x,
                pos_text_y,
                r"$\Delta = %s$" % (f"{diff_median_percent:.1f}") + "% ; " + p_text,
                ha="center",
                va="center",
                transform=ax.transAxes,

            )
    if ax is None:
        ax = fancy_violins(df, **kwargs)
    else:
        fancy_violins(df,ax=ax, **kwargs)

    if logscale:
        ax.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(_ticklabels_lin_to_log10)
        )
        ax.yaxis.set_major_locator(matplotlib.ticker.MultipleLocator(1))

    if xlabels is not None:
        assert isinstance(xlabels, (list, tuple))
        assert len(xlabels) == len(labels)
        ax.set_xticklabels(xlabels)

    ax.set_xlabel("")
    if plot_ylabel:
        ax.set_ylabel(y_labels[obs]) 
    else: 
        ax.set_ylabel(y_labels_short[obs]) 

    # remove axis
    ax.yaxis.set_ticks_position("none")
    ax.xaxis.set_ticks_position("none")
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_visible(False)

    # obseravble level customization
    if areawise_plot:
        if obs == "R_tot":
            ax.set_ylim(-0.08, 0.4)
        elif obs == "tau_R" and logscale:
            ax.set_ylim(-0.5, 3)
        elif obs == "tau_double" and logscale:
            ax.set_ylim(-0.5, 4)
    else: 
        if obs == "R_tot":
            ax.set_ylim(-0.08, None)
        elif "tau_" in obs and logscale:
            ax.set_ylim(-0.5, None)

    # grid
    ax.grid(axis="y", color="0.9", linestyle="-", linewidth=1)
    ax.set_axisbelow(True)

    # area name and N neurons for each row
    if obs == "tau_double":
        y_text = 0.88
        # y_max = 1501
        # y_min = -(y_max / 100)
        if areawise_plot:
            ax.text(x_area_name, 2.5, area_name, weight='bold')#, usetex = True )
            ax.text(x_area_name, 1.5, r"$n = %d$"%N)#, usetex = True)


    # text_kwargs = dict(
    #     s=r"$\it{N} = " + str(N) + r"$",
    #     fontsize=8,
    #     color="black",
    #     transform=ax.transAxes,
    # )
    # ax.text(0.5, 0.05, ha="center", va="bottom", **text_kwargs)

    return ax


def panel_selectivity_scatter(df, observable, selectivity_metric, color="#233954", ax=None, point_size = 0.5, plot_xlabel = True, plot_ylabel = True, plot_areaname = False, **kwargs):

    assert selectivity_metric in df.columns, f"{selectivity_metric} not in columns, `load_metrics()` first"
    kwargs = kwargs.copy()

    if "bonferroni_correction" in kwargs.keys():
        bonferroni_correction  = kwargs["bonferroni_correction"]
    else: 
        bonferroni_correction = 1

    # aviod nans
    len_before = len(df)
    df = df.query(f"{observable} == {observable}")
    df = df.query(f"{selectivity_metric} == {selectivity_metric}")
    len_after = len(df)
    log.info(f"dropped {len_before - len_after} rows with nan")

    if "tau_" in observable:
        # seconds to ms
        df[observable] = df[observable] * 1000

    if ax == None:
        fig, ax = plt.subplots()
        print("passing ax failed")
    ax.scatter(df[selectivity_metric], df[observable], s=point_size, alpha=0.5, lw=0, rasterized=True, c=color)
    ax.set_ylim(0, 0.2)
    # ax.set_xscale("log")

    r, p_val = scipy.stats.pearsonr(df[selectivity_metric], df[observable])
    m, b = np.polyfit(df[selectivity_metric], df[observable], 1)

    log.info(f"r: {r:.3f}, p: {p_val:.2g}, m: {m:.3f}, b: {b:.3f}")
    if p_val < 0.05 * bonferroni_correction:
        ax.plot(df[selectivity_metric], m * df[selectivity_metric] + b, lw=1.0, color=color)

    pos_text_x = 0.95
    if observable == "tau_double":
        y_text = 0.88
        y_max = 1501
        y_min = -(y_max / 100)
        if plot_areaname:
            area_name = kwargs["area_name"]
            x_text = kwargs["x_text"]
            N_units = len(df)
            ax.text(x_text,750, area_name, weight='bold')#, usetex = True )
            ax.text(x_text,500, r"$n = %d$"%N_units)#, usetex = True)
    elif observable == "tau_R":
        y_text = 0.88
        y_max = 201
        y_min = -(y_max / 100)
    elif observable == "R_tot":
        y_text = 0.2
        y_max = 0.3
        y_min = -(y_max / 100)

    ax.grid(axis="y", color="0.9", linestyle="-", linewidth=1)
    ax.set_axisbelow(True)

    sns.despine(ax=ax, left=True, bottom=False, offset=5)

    ax.yaxis.set_ticks_position("none")
    ax.spines["left"].set_visible(False)

  
    ax.set_ylim(y_min, y_max*1.03)
    if observable == "tau_double":
        ax.set_yticks([0, 500, 1000, 1500])
    elif observable == "tau_R":
        ax.set_yticks([0, 100, 200])
    elif observable == "R_tot":
        ax.set_yticks([0, 0.1, 0.2, 0.3])
        

    if selectivity_metric == "g_dsi_dg":
        if plot_xlabel:
            ax.set_xlabel("direction selectivity")
        ax.set_xlim(0, 1.0)
        ax.xaxis.set_major_locator(plt.MultipleLocator(0.25))
    elif selectivity_metric == "image_selectivity_ns":
        if plot_xlabel:
            ax.set_xlabel("image selectivity")
        ax.set_xlim(-0.3, 1.0)
        ax.xaxis.set_major_locator(plt.MultipleLocator(0.3))
        y_text = 0.88
    if plot_ylabel:
        ax.set_ylabel(y_labels[observable]) 
    else: 
        ax.set_ylabel(y_labels_short[observable]) 

    # only give correlation and p value if p_val is significant
    if p_val < 0.05*bonferroni_correction:
        if p_val >= 1e-8:
            p_val_text = r"$\it{p}$ = " + _format_base_ten(p_val)
        else:
            p_val_text = r"$\it{p} < 10^{-8}$"

        ax.text(
            pos_text_x,
            y_text,
            r"$\it{r} = %s$" % (f"{r:.2f}") + "; " + p_val_text,
            ha="right",
            va="center",
            transform=ax.transAxes,
        )

    return ax


# ------------------------------------------------------------------------------ #
# plotting helpers
# ------------------------------------------------------------------------------ #


def fancy_violins(
    df,
    category,
    observable,
    ax=None,
    num_swarm_points=400,
    same_points_per_swarm=True,
    swarm_spacing=0.0,
    replace=False,
    palette=None,
    seed=42,
    violin_kwargs=dict(),
    swarm_kwargs=dict(),
):
    """
    Multiple violins that are split into a left smooth kernel density estimate
    and a swarm plot on the right.

    hacked version of seaborns swarm and violinplots.

    # Parameters
    """

    if sns.__version__ > "0.11.2":
        log.warning("seaborn version is above 0.11.2, may break the violin plot")

    violin_kwargs = violin_kwargs.copy()
    swarm_kwargs = swarm_kwargs.copy()

    np.random.seed(seed)

    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.get_figure()

    ax.set_rasterization_zorder(-5)

    categories = df[category].unique()
    if palette is not None:
        categories = [c for c in palette.keys() if c in categories]

    # we want half violins, so hack the data and abuse seaborns "hue" and "split"
    df["fake_hue"] = 0
    for cat in categories:
        # create a dataframe with a single row of nans and all columns matching the original
        dummy = df.iloc[0:1].copy()
        for col in dummy.columns:
            dummy[col] = np.nan
        dummy["fake_hue"] = 1
        dummy[category] = cat
    df = pd.concat([df, dummy], ignore_index=True)
    global debug_df
    debug_df = dummy
    # log.debug(df)

    # lets use that seaborn looks up the `hue` variable as the key in palette dict,
    # maybe matching our global colors
    if palette is None:
        palette = {
            "cortex": sns.color_palette().as_hex()[0],
            "thalamus": sns.color_palette().as_hex()[1],
            "natural_movie_one_more_repeats": sns.color_palette().as_hex()[0],
            "spontaneous": sns.color_palette().as_hex()[1],
            "tau_offset_accepted": sns.color_palette().as_hex()[0],
            "tau_offset_rejected": sns.color_palette().as_hex()[0],
            "tau_two_timescales": sns.color_palette().as_hex()[1],
            "tau_rejected": sns.color_palette().as_hex()[1],
        }

    light_palette = dict()
    for key in palette.keys():
        try:
            light_palette[key] = _alpha_to_solid_on_bg(palette[key], 0.5)
        except:
            # if we have keys that are not colors
            light_palette[key] = palette[key]

    violin_defaults = dict(
        scale_hue=False,
        cut=0,
        scale="width",
        inner=None,
        bw=0.1,
        # palette=light_palette,
        hue="fake_hue",
        split=True,
    )

    for key in violin_defaults.keys():
        violin_kwargs.setdefault(key, violin_defaults[key])

    sns.violinplot(x=category, y=observable, data=df, ax=ax, **violin_kwargs)

    # remove the dummy row we added
    df = df.query("fake_hue == 0")

    ylim = ax.get_ylim()

    # prequerry the data frames via category
    sub_dfs = dict()
    max_points = 0
    for idx, cat in enumerate(categories):
        if type(cat) == str:
            df_for_cat = df.query(f"`{category}` == '{cat}'")
        else:
            df_for_cat = df.query(f"`{category}` == {cat}")
        sub_dfs[cat] = df_for_cat

        # for the swarm plot, fetch max height so we could tweak number of points and size
        hist, bins = np.histogram(df_for_cat[observable], _unit_bins(ylim[0], ylim[1]))
        max_points = np.max([max_points, np.max(hist)])

    # update the color of the categories.
    # this is a bit hairy - we need to find the PolyCollection and Line2D objects
    # and depending on the violin shape, the type changes.
    cats_fixed = 0
    for child in ax.get_children():
        if isinstance(child, matplotlib.collections.PolyCollection):
            child.set_color(light_palette[categories[cats_fixed]])
            child.set_edgecolor(palette[categories[cats_fixed]])
            child.set_linewidth(1.0)
            cats_fixed += 1
        elif isinstance(child, matplotlib.lines.Line2D):
            child.set_color(palette[categories[cats_fixed]])
            child.set_linewidth(1.0)
            cats_fixed += 1
        if cats_fixed == len(categories):
            break

    for idx, cat in enumerate(categories):
        ax.collections[idx].set_color(light_palette[cat])
        ax.collections[idx].set_edgecolor(palette[cat])
        ax.collections[idx].set_linewidth(1.0)

        # custom error estimates
        df_for_cat = sub_dfs[cat]

        samples = _pd_bootstrap(
            df_for_cat,
            obs=observable,
            num_boot=500,
        )
        median = np.median(samples)
        quantiles = np.quantile(samples, [0.025, 0.975])

        log.debug(
            f"{cat} median: {median:.4f} quantiles: {quantiles} from"
            f" {len(samples)} samples of length {len(df_for_cat)}"
        )

        log.debug(
            f"{cat} min: {np.min(df_for_cat[observable]):.2g} max:"
            f" {np.max(df_for_cat[observable]):.2g}"
        )

        # this may also happen when category variable is not defined.
        _draw_error_stick(
            ax,
            center=idx,
            mid=median,
            errors=[quantiles[0], quantiles[1]],
            orientation="v",
            color=palette[cat],
            zorder=2,
        )

    # swarms
    swarm_defaults = dict(
        size=1.4,
        # palette=light_palette,
        palette=palette,
        order=categories,
        zorder=1,
        edgecolor=(1.0, 1.0, 1.0, 1.0),
        linewidth=0.2,
    )

    for key in swarm_defaults.keys():
        swarm_kwargs.setdefault(key, swarm_defaults[key])

    # so, for the swarms, we may want around the same number of points per swarm
    # then, apply subsampling for each category!
    if same_points_per_swarm:
        merged_df = []
        for idx, cat in enumerate(categories):
            if type(cat) == str:
                sub_df = df.query(f"`{category}` == '{cat}'")
            else:
                sub_df = df.query(f"`{category}` == {cat}")
            if not replace:
                num_samples = np.min([num_swarm_points, len(sub_df)])
            else:
                num_samples = num_swarm_points
            merged_df.append(
                sub_df.sample(
                    n=num_samples,
                    replace=replace,
                    # ignore_index=True,
                )
            )
        merged_df = pd.concat(merged_df, ignore_index=True)

    else:
        if not replace:
            num_samples = np.min([num_swarm_points, len(df)])
        else:
            num_samples = num_swarm_points
        merged_df = df.sample(n=num_samples, replace=replace)  # , ignore_index=True)

    log.debug(f"plotting {len(merged_df)} points for cat {category}")

    # sns uses the linewidth to calcultate the spacing
    # we add and later substracted to linewidth.
    original_lw = swarm_kwargs["linewidth"]
    swarm_kwargs["linewidth"] += swarm_spacing

    sns.swarmplot(
        x=category,
        y=observable,
        data=merged_df,
        ax=ax,
        **swarm_kwargs,
    )

    # move the swarms slightly to the right and throw away left half
    for idx, cat in enumerate(categories):
        c = ax.collections[-len(categories) + idx]
        offsets = c.get_offsets()
        odx = np.where(offsets[:, 0] > idx)
        offsets = offsets[odx]
        offsets[:, 0] += 0.05
        c.set_offsets(offsets)
        # re-adjust the linewidth of the swarm points
        c.set_linewidths(original_lw)

    ax.get_legend().set_visible(False)

    return ax


def _draw_error_stick(
    ax,
    center,
    mid,
    errors,
    outliers=None,
    orientation="v",
    linewidth=1.5,
    **kwargs,
):
    """
    Use this to draw errors likes seaborns nice error bars, but using our own
    error estimates.

    note: seaborn v 0.12 broke my swarmplot hack. `conda install seaborn=0.11.2`

    # Parameters
    ax : axis element
    center : number,
        where to align in off-data direction.
        seaborn uses integers 0, 1, 2, ... when plotting categorial violins.
    mid : float,
        middle data point to draw (white dot)
    errors : array like, length 2
        thick bar corresponding to errors
    outliers : array like, length 2
        thin (longer) bar corresponding to outliers
    orientation : "v" or "h"
    **kwargs are passed through to `ax.plot`
    """

    kwargs = kwargs.copy()
    kwargs.setdefault("color", "black")
    kwargs.setdefault("zorder", 3)
    kwargs.setdefault("clip_on", False)

    if outliers is not None:
        assert len(outliers) == 2
        if orientation == "h":
            ax.plot(outliers, [center, center], linewidth=linewidth, **kwargs)
        else:
            ax.plot([center, center], outliers, linewidth=linewidth, **kwargs)

    assert len(errors) == 2
    if orientation == "h":
        ax.plot(errors, [center, center], linewidth=linewidth * 3, **kwargs)
    else:
        ax.plot([center, center], errors, linewidth=linewidth * 3, **kwargs)

    kwargs["zorder"] += 1
    kwargs["edgecolor"] = kwargs["color"]
    kwargs["color"] = "white"
    if orientation == "h":
        ax.scatter(mid, center, s=np.square(linewidth * 2), **kwargs)
    else:
        ax.scatter(center, mid, s=np.square(linewidth * 2), **kwargs)


def _pd_bootstrap(
    df,
    obs,
    sample_size=None,
    num_boot=1000,
    f_within_sample=np.nanmedian,
):
    """
    bootstrap across all rows of a dataframe to get an estimate across
    many samples and standard error of this estimate.
    query the dataframe first to filter for the right conditions.

    # Parameters:
    obs : str, the column to estimate for
    sample_size: int or None, default (None) for samples that are as large
        as the original dataframe (number of rows)
    num_boot : int, how many bootstrap samples to generate
    f_within_sample : function, default np.nanmedian is used to calculate the estimate
        for each sample

    # Returns:
    resampled_estaimtes : a list of length num_boot where `f_within_sample` ˙as been
        applied to each bootstrap sample

    """

    if sample_size is None:
        sample_size = np.fmin(len(df), 10_000)

    # drop nans
    df = df.query(f"`{obs}` == `{obs}`")

    resampled_estimates = []
    for idx in range(0, num_boot):
        sample_df = df.sample(
            n=sample_size, replace=True, ignore_index=True, random_state=42 + idx
        )
        resampled_estimates.append(f_within_sample(sample_df[obs]))

    return resampled_estimates


def _x_pos(which):
    """
    dirty helper to get decently aligned x positions for both structure groups
    and area-level markers (for the `panel_areas_grouped` function)

    # Parameters
    which : str
        any of "thalamus_grouped", "V1_grouped", "higher_grouped", or a structure name like "LGN"

    # Returns
    x_pos : either a float (for structure names) or
        a tuple of left, center, right for area-level markers
    """

    x_pos = [-0.2, 0.75, 2]

    # lets say 0.5 between groups
    gdx = 0.5
    # lets say 0.25 between in-group markers
    mdx = 0.25
    # padding around group edges
    pdx = 0.1

    x_pos = {}
    _ref = pdx

    x_pos["thalamus_grouped"] = {
        "groupleft": _ref - pdx,
        "groupright": _ref + 2 * mdx + pdx,
        "groupmarker": _ref + 2 * mdx,
        "LGN": _ref,
        "LP": _ref + 1 * mdx,
    }
    _ref = x_pos["thalamus_grouped"]["groupright"] + gdx + pdx

    x_pos["V1_grouped"] = {
        "groupleft": _ref - pdx,
        "groupright": _ref + 1.5 * mdx + pdx,
        "groupmarker": np.nan,
        "V1": _ref + 0.75 * mdx,
    }
    _ref = x_pos["V1_grouped"]["groupright"] + gdx + pdx

    x_pos["higher_grouped"] = {
        "groupleft": _ref - pdx,
        "groupmarker": _ref,
        "groupright": _ref + 5 * mdx + pdx,
        "LM": _ref + 1 * mdx,
        "RL": _ref + 2 * mdx,
        "AL": _ref + 3 * mdx,
        "PM": _ref + 4 * mdx,
        "AM": _ref + 5 * mdx,
    }

    if which in ["thalamus_grouped", "V1_grouped", "higher_grouped"]:
        return (
            x_pos[which]["groupleft"],
            x_pos[which]["groupmarker"],
            x_pos[which]["groupright"],
        )
    else:
        for area in x_pos.keys():
            if which in x_pos[area].keys():
                return x_pos[area][which]


def _unit_bins(low=0, high=1, num_bins=20):
    bw = (high - low) / num_bins
    return np.arange(low, high + 0.1 * bw, bw)


def _alpha_to_solid_on_bg(base, alpha, bg="white"):
    """
    Probide a color to start from `base`, and give it opacity `alpha` on
    the background color `bg`.
    """

    def rgba_to_rgb(c, bg):
        bg = matplotlib.colors.to_rgb(bg)
        alpha = c[-1]

        res = (
            (1 - alpha) * bg[0] + alpha * c[0],
            (1 - alpha) * bg[1] + alpha * c[1],
            (1 - alpha) * bg[2] + alpha * c[2],
        )
        return res

    new_base = list(matplotlib.colors.to_rgba(base))
    new_base[3] = alpha
    return matplotlib.colors.to_hex(rgba_to_rgb(new_base, bg))


def _ticklabels_lin_to_log10_power(x, pos, nicer=True, nice_range=[-1, 0, 1]):
    """
    converts ticks of manually logged data (lin ticks) to log ticks, as follows
     1 -> 10^1
     0 -> 10^0
    -1 -> 10^-1
    """
    if x.is_integer():
        # use easy to read formatter if exponents are close to zero
        if nicer and x in nice_range:
            return _ticklabels_lin_to_log10(x, pos)
        else:
            return r"$10^{{{:d}}}$".format(int(x))
    else:
        return ""


def _ticklabels_lin_to_log10(x, pos):
    """
    converts ticks of manually logged data (lin ticks) to log ticks, as follows
     1 -> 10
     0 -> 1
    -1 -> 0.1

    # Example
    ```
    ax.xaxis.set_major_formatter(
        matplotlib.ticker.FuncFormatter(ticklabels_lin_to_log10_power)
    )
    ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(1))
    ax.xaxis.set_minor_locator(ticklocator_lin_to_log_minor())
    ```
    """
    prec = int(np.ceil(-np.minimum(x, 0)))
    return "{{:.{:1d}f}}".format(prec).format(np.power(10.0, x))


def _format_base_ten(x):
    """
    Input a float, get a string representation that is formatted
    to 3.5 x 10^3
    """
    if x == 0:
        return "0"
    else:
        a = np.floor(np.log10(np.abs(x)))
        b = x / 10**a
        if abs(a) < 3:
            return "{:.3f}".format(x)

        return r"${:.1f} \times 10^{{{}}}$".format(b, int(a))



from arviz.data import convert_to_dataset
from arviz.labels import BaseLabeller
from arviz.sel_utils import xarray_var_iter
from arviz.utils import _var_names, get_coords
from arviz.rcparams import rcParams
from arviz.plots.plot_utils import default_grid, filter_plotters_list, get_plotting_function
from arviz.plots.backends.matplotlib import matplotlib_kwarg_dealiaser
import seaborn as sns

def plot_posterior(
    data,
    var_names=None,
    filter_vars=None,
    transform=None,
    coords=None,
    figsize=None,
    textsize=None,
    hdi=True,
    hdi_prob=0.95,
    multimodal=False,
    round_to=2,
    point_estimate="median",
    group="posterior",
    rope=None,
    ref_val=None,
    kind="kde",
    bw=0.05,
    bins=None,
    ax=None,
    show=None,
    credible_interval=None,
    **kwargs,
):

    data = convert_to_dataset(data, group="posterior")
    if transform is not None:
        data = transform(data)

    coords = {}

    plotters = filter_plotters_list(
        list(
            xarray_var_iter(
                get_coords(data, coords=coords), var_names=var_names, combined=True
            )
        ),
        "plot_posterior",
    )

    length_plotters = len(plotters)
    rows, cols = default_grid(length_plotters)

    (
    figsize,
    ax_labelsize,
    titlesize,
    xt_labelsize,
    linewidth,
    _,
    ) = az.plots.plot_utils._scale_fig_size(figsize, textsize, rows, cols)
    kwargs = matplotlib_kwarg_dealiaser(kwargs, "plot")
    kwargs.setdefault("linewidth", linewidth)

    # for (var_name, selection, isel, x), _ax in zip(plotters, np.ravel(ax)):
    for (var_name, selection, isel, x) in plotters:
        values = x.flatten()

        if len(plotters) > 1: 
            kwargs["color"] = sns.color_palette()[selection["session"] % 10]
        # density
        az.plot_kde(
            values,
            bw=bw,
            fill_kwargs={"alpha": kwargs.pop("fill_alpha", 0)},
            plot_kwargs=kwargs,
            ax=ax,
            rug=False,
            show=False,
        )
        
        plot_height = ax.get_ylim()[1]

        # hdi
        if hdi:
            hdi_probs = az.stats.stats.hdi(
                values, hdi_prob=hdi_prob, multimodal=multimodal
            )  # type: np.ndarray

            for hdi_i in np.atleast_2d(hdi_probs):
                ax.plot(
                    hdi_i,
                    (plot_height * 0.02, plot_height * 0.02),
                    lw=linewidth * 2,
                    color="k",
                    solid_capstyle="butt",
                )

            # median
            point_value = az.plots.plot_utils.calculate_point_estimate(
                point_estimate, values, bw
            )
            print("median: ", point_value)
            ax.plot(point_value, plot_height * 0.02, "o", color="red")
            
    ax.yaxis.set_ticks([])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_visible(True)
    ax.xaxis.set_ticks_position("bottom")
    ax.tick_params(
        axis="x",
        direction="out",
        width=1,
        length=3,
        color="0.5",
        labelsize=xt_labelsize,
    )
    ax.spines["bottom"].set_color("0.5")

