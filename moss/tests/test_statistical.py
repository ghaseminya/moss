import numpy as np
import scipy as sp
from scipy import stats as spstats
from matplotlib.mlab import psd

from numpy.testing import assert_array_equal, assert_array_almost_equal
import numpy.testing as npt
import nose.tools
from nose.tools import assert_equal, raises

from .. import statistical as stat


a_norm = np.random.randn(100)

a_range = np.arange(101)


def test_bootstrap():
    """Test that bootstrapping gives the right answer in dumb cases."""
    a_ones = np.ones(10)
    n_boot = 5
    out1 = stat.bootstrap(a_ones, n_boot=n_boot)
    assert_array_equal(out1, np.ones(n_boot))
    out2 = stat.bootstrap(a_ones, n_boot=n_boot, func=np.median)
    assert_array_equal(out2, np.ones(n_boot))


def test_bootstrap_length():
    """Test that we get a bootstrap array of the right shape."""
    out = stat.bootstrap(a_norm)
    assert_equal(len(out), 10000)

    n_boot = 100
    out = stat.bootstrap(a_norm, n_boot=n_boot)
    assert_equal(len(out), n_boot)


def test_bootstrap_range():
    """Test that boostrapping a random array stays within the right range."""
    min, max = a_norm.min(), a_norm.max()
    out = stat.bootstrap(a_norm)
    nose.tools.assert_less_equal(min, out.min())
    nose.tools.assert_greater_equal(max, out.max())


def test_bootstrap_multiarg():
    """Test that bootstrap works with multiple input arrays."""
    x = np.vstack([[1, 10] for i in range(10)])
    y = np.vstack([[5, 5] for i in range(10)])

    test_func = lambda x, y: np.vstack((x, y)).max(axis=0)
    out_actual = stat.bootstrap(x, y, n_boot=2, func=test_func)
    out_wanted = np.array([[5, 10], [5, 10]])
    assert_array_equal(out_actual, out_wanted)


def test_bootstrap_axis():
    """Test axis kwarg to bootstrap function."""
    x = np.random.randn(10, 20)
    n_boot = 100
    out_default = stat.bootstrap(x, n_boot=n_boot)
    assert_equal(out_default.shape, (n_boot,))
    out_axis = stat.bootstrap(x, n_boot=n_boot, axis=0)
    assert_equal(out_axis.shape, (n_boot, 20))


def test_smooth_bootstrap():
    """Test smooth bootstrap."""
    x = np.random.randn(15)
    n_boot = 100
    out_normal = stat.bootstrap(x, n_boot=n_boot, func=np.median)
    out_smooth = stat.bootstrap(x, n_boot=n_boot,
                                smooth=True, func=np.median)
    assert(np.median(out_normal) in x)
    assert(not np.median(out_smooth) in x)


def test_bootstrap_ols():
    """Test bootstrap of OLS model fit."""
    ols_fit = lambda X, y: np.dot(np.dot(np.linalg.inv(
                                  np.dot(X.T, X)), X.T), y)
    X = np.column_stack((np.random.randn(50, 4), np.ones(50)))
    w = [2, 4, 0, 3, 5]
    y_noisy = np.dot(X, w) + np.random.randn(50) * 20
    y_lownoise = np.dot(X, w) + np.random.randn(50)

    n_boot = 500
    w_boot_noisy = stat.bootstrap(X, y_noisy,
                                  n_boot=n_boot,
                                  func=ols_fit)
    w_boot_lownoise = stat.bootstrap(X, y_lownoise,
                                     n_boot=n_boot,
                                     func=ols_fit)

    assert_equal(w_boot_noisy.shape, (n_boot, 5))
    assert_equal(w_boot_lownoise.shape, (n_boot, 5))
    nose.tools.assert_greater(w_boot_noisy.std(),
                              w_boot_lownoise.std())


@raises(ValueError)
def test_bootstrap_arglength():
    """Test that different length args raise ValueError."""
    stat.bootstrap(range(5), range(10))


@raises(TypeError)
def test_bootstrap_noncallable():
    """Test that we get a TypeError with noncallable statfunc."""
    non_func = "mean"
    stat.bootstrap(a_norm, 100, non_func)


def test_percentiles():
    """Test function to return sequence of percentiles."""
    single_val = 5
    single = stat.percentiles(a_range, single_val)
    assert_equal(single, single_val)

    multi_val = [10, 20]
    multi = stat.percentiles(a_range, multi_val)
    assert_array_equal(multi, multi_val)

    array_val = np.random.randint(0, 101, 5).astype(float)
    array = stat.percentiles(a_range, array_val)
    assert_array_almost_equal(array, array_val)


def test_percentiles_acc():
    """Test accuracy of calculation."""
    # First a basic case
    data = np.array([10, 20, 30])
    val = 20
    perc = stat.percentiles(data, 50)
    assert_equal(perc, val)

    # Now test against scoreatpercentile
    percentiles = np.random.randint(0, 101, 10)
    out = stat.percentiles(a_norm, percentiles)
    for score, pct in zip(out, percentiles):
        assert_equal(score, sp.stats.scoreatpercentile(a_norm, pct))


def test_percentiles_axis():
    """Test use of axis argument to percentils."""
    data = np.random.randn(10, 10)

    # Test against the median with 50th percentile
    median1 = np.median(data)
    out1 = stat.percentiles(data, 50)
    assert_array_almost_equal(median1, out1)

    for axis in range(2):
        median2 = np.median(data, axis=axis)
        out2 = stat.percentiles(data, 50, axis=axis)
        assert_array_almost_equal(median2, out2)

    median3 = np.median(data, axis=0)
    out3 = stat.percentiles(data, [50, 95], axis=0)
    assert_array_almost_equal(median3, out3[0])
    assert_equal(2, len(out3))


def test_add_constant():
    """Test the add_constant function."""
    a = np.random.randn(10, 5)
    wanted = np.column_stack((a, np.ones(10)))
    got = stat.add_constant(a)
    assert_array_equal(wanted, got)


def test_highpass_matrix_shape():
    """Test the filter matrix is the right shape."""
    for n_tp in 10, 100:
        F = stat.fsl_highpass_matrix(n_tp, 50)
        assert_equal(F.shape, (n_tp, n_tp))


def test_filter_matrix_diagonal():
    """Test that the filter matrix has strong diagonal."""
    F = stat.fsl_highpass_matrix(10, 3)
    assert_array_equal(F.argmax(axis=1).squeeze(), np.arange(10))


def test_filtered_data_shape():
    """Test that filtering data returns same shape."""
    data = np.random.randn(100)
    data_filt = stat.fsl_highpass_filter(data, 30)
    assert_equal(data.shape, data_filt.shape)

    data = np.random.randn(100, 3)
    data_filt = stat.fsl_highpass_filter(data, 30)
    assert_equal(data.shape, data_filt.shape)


def test_filter_psd():
    """Test highpass filter with power spectral density."""
    a = np.sin(np.linspace(0, 4 * np.pi, 100))
    b = np.random.randn(100) / 2
    y = a + b
    y_filt = stat.fsl_highpass_filter(y, 10)
    assert_equal(y.shape, y_filt.shape)

    orig_psd, _ = psd(y, 2 ** 5)
    filt_psd, _ = psd(y_filt, 2 ** 5)

    nose.tools.assert_greater(orig_psd[:3].mean(), filt_psd[:3].mean())


def test_filter_strength():
    """Test that lower cutoff makes filter more aggresive."""
    a = np.sin(np.linspace(0, 4 * np.pi, 100))
    b = np.random.randn(100) / 2
    y = a + b

    cutoffs = np.linspace(20, 80, 5)
    densities = np.zeros_like(cutoffs)
    for i, cutoff in enumerate(cutoffs):
        filt = stat.fsl_highpass_filter(y, cutoff)
        density, _ = psd(filt, 2 ** 5)
        densities[i] = density.mean()

    assert_array_equal(densities, np.sort(densities))


def test_filter_copy():
    """Test that copy argument to filter function works."""
    a = np.random.randn(100, 10)
    a_copy = stat.fsl_highpass_filter(a, 50, copy=True)
    assert(not (a == a_copy).all())
    a_nocopy = stat.fsl_highpass_filter(a, 100, copy=False)
    assert_array_equal(a, a_nocopy)


def test_randomize_onesample():
    """Test performance of randomize_onesample."""
    a_zero = np.random.normal(0, 1, 50)
    t_zero, p_zero = stat.randomize_onesample(a_zero)
    nose.tools.assert_greater(p_zero, 0.05)

    a_five = np.random.normal(5, 1, 50)
    t_five, p_five = stat.randomize_onesample(a_five)
    nose.tools.assert_greater(0.05, p_five)

    t_scipy, p_scipy = sp.stats.ttest_1samp(a_five, 0)
    nose.tools.assert_almost_equal(t_scipy, t_five)


def test_randomize_onesample_range():
    """Make sure that output is bounded between 0 and 1."""
    for i in xrange(100):
        a = np.random.normal(np.random.randint(-10, 10),
                             np.random.uniform(.5, 3), 100)
        t, p = stat.randomize_onesample(a, 100)
        nose.tools.assert_greater_equal(1, p)
        nose.tools.assert_greater_equal(p, 0)


def test_randomize_onesample_getdist():
    """Test that we can get the null distribution if we ask for it."""
    a = np.random.normal(0, 1, 20)
    out = stat.randomize_onesample(a, return_dist=True)
    assert_equal(len(out), 3)


def test_randomize_onesample_iters():
    """Make sure we get the right number of samples."""
    a = np.random.normal(0, 1, 20)
    t, p, samples = stat.randomize_onesample(a, return_dist=True)
    assert_equal(len(samples), 10000)
    for n in np.random.randint(5, 1e4, 5):
        t, p, samples = stat.randomize_onesample(a, n, return_dist=True)
        assert_equal(len(samples), n)


def test_randomize_onesample_seed():
    """Test that we can seed the random state and get the same distribution."""
    a = np.random.normal(0, 1, 20)
    seed = 42
    t_a, p_a, samples_a = stat.randomize_onesample(a, 1000, seed, True)
    t_b, t_b, samples_b = stat.randomize_onesample(a, 1000, seed, True)
    assert_array_equal(samples_a, samples_b)


def test_randomize_corrmat():
    """Test the correctness of the correlation matrix p values."""
    a = np.random.randn(30)
    b = a + np.random.rand(30) * 3
    c = np.random.randn(30)
    d = [a, b, c]

    p_mat, dist = stat.randomize_corrmat(d, corrected=False, return_dist=True)
    nose.tools.assert_greater(p_mat[1, 0], p_mat[2, 0])

    corrmat = np.corrcoef(d)
    pctile = spstats.percentileofscore(dist[2, 1], corrmat[2, 1])
    nose.tools.assert_almost_equal(p_mat[2, 1] * 100, pctile)

    d[1] = -a + np.random.rand(30)
    p_mat = stat.randomize_corrmat(d)
    nose.tools.assert_greater(0.05, p_mat[1, 0])


def test_randomize_corrmat_dist():
    """Test that the distribution looks right."""
    a = np.random.randn(3, 20)
    for n_i in [5, 10]:
        p_mat, dist = stat.randomize_corrmat(a, n_iter=n_i, return_dist=True)
        assert_equal(n_i, dist.shape[-1])

    p_mat, dist = stat.randomize_corrmat(a, n_iter=10000, return_dist=True)

    diag_mean = dist[0, 0].mean()
    assert_equal(diag_mean, 1)

    off_diag_mean = dist[0, 1].mean()
    nose.tools.assert_greater(0.05, off_diag_mean)

    skew, skewp = spstats.skewtest(dist[0, 1])
    nose.tools.assert_greater(skewp, 0.1)


def test_randomize_corrmat_correction():
    """Test that FWE correction works."""
    a = np.random.randn(3, 20)
    p_mat = stat.randomize_corrmat(a, False)
    p_mat_corr = stat.randomize_corrmat(a, True)
    triu = np.triu_indices(3, 1)
    npt.assert_array_less(p_mat_corr[triu], p_mat[triu])


def test_randomise_corrmat_seed():
    """Test that we can seed the corrmat randomization."""
    a = np.random.randn(3, 20)
    _, dist1 = stat.randomize_corrmat(a, random_seed=0, return_dist=True)
    _, dist2 = stat.randomize_corrmat(a, random_seed=0, return_dist=True)
    assert_array_equal(dist1, dist2)
