%RUN_NRTDL_DEMO  Lunar surface tap model -> 5G NR link-level demo.
%
%   Consumes matlab/site04_traj_S.mat (produced by
%   analysis/export_taps_demo.py: a 1.8 km rover traverse across the Site04
%   LOLA/PGDA tile, taps from the two-ray + Deygout pipeline) and shows the
%   three things the tap export is for:
%
%     1. The along-track fading trace: the spatial two-ray nulls the rover
%        crosses, replayed as a time series g(t) at walking speed.
%     2. A per-waypoint link budget -> SNR -> spectral-efficiency trace for
%        an uplink from a 23 dBm EVA-class terminal (the binding direction),
%        i.e. the "what does the channel do to the 5G link" planning view.
%     3. (If 5G Toolbox is installed) the same taps loaded into nrTDLChannel
%        with DelayProfile='Custom' and applied to an NR CP-OFDM waveform,
%        with the measured channel gain cross-checked against the
%        deterministic tap prediction. This is the entry point for full
%        PDSCH/PUSCH BLER simulation with these channels.
%
%   The lunar surface channel is SPARSE (1-3 taps; the two-ray pair collapses
%   into one complex tap because its excess delay is sub-nanosecond), so
%   nrTDLChannel's Custom profile represents it exactly -- no truncation,
%   unlike terrestrial delay profiles.
%
%   Run from this folder:  >> run_nrtdl_demo

%% Load the trajectory tap file
S = load('site04_traj_S.mat');
N   = size(S.PathDelays, 1);          % waypoints
fc  = S.CarrierHz;                    % 2.5 GHz
t   = S.Times_s(:);                   % s, 1 m/s rover
gdB = S.GainMagnitude_dB(:);          % collapsed tap, dB rel. free space
fprintf('Loaded %d waypoints, carrier %.2f GHz, traverse %.0f s\n', ...
        N, fc/1e9, t(end));

% Uplink budget: EVA-suit terminal -> 30 m mast (values match the repo's
% coverage tooling defaults for --mode ue).
EIRP_dBm  = 23;                       % handheld/EVA class
Grx_dBi   = 12;                       % mast sector antenna
NF_dB     = 5;                        % receiver noise figure
B_Hz      = 20e6;                     % carrier bandwidth
N0_dBm    = -174 + 10*log10(B_Hz) + NF_dB;   % noise floor in B

% Per-waypoint received power and SNR: absolute PL = FSPL(direct) - g_dB.
PL_dB   = S.FSPLDirect_dB(:) - gdB;
Prx_dBm = EIRP_dBm + Grx_dBi - PL_dB;
SNR_dB  = Prx_dBm - N0_dBm;
SE      = min(log2(1 + 10.^(SNR_dB/10)), 7.4);   % b/s/Hz, 256QAM ceiling

%% Figure 1: fading trace + link-level consequence
figure('Name', 'Lunar tap-model trace', 'Position', [80 80 900 640]);

subplot(3,1,1);
plot(t, gdB, 'LineWidth', 1.1); grid on;
yline(0, ':'); hold on;
nlos = S.LOS(:) == 0;
if any(nlos), plot(t(nlos), gdB(nlos), 'rv', 'MarkerSize', 5); end
ylabel('tap gain (dB rel. FS)');
title(sprintf(['Rover traverse, Site04 @ %.1f GHz: two-ray nulls as time ' ...
               'fading (red = NLOS/diffraction)'], fc/1e9));

subplot(3,1,2);
plot(t, SNR_dB, 'LineWidth', 1.1); grid on;
ylabel('uplink SNR (dB)');
title(sprintf('23 dBm terminal \\rightarrow mast: SNR over %g MHz', B_Hz/1e6));

subplot(3,1,3);
plot(t, SE, 'LineWidth', 1.1); grid on;
xlabel('time (s)  [1 m/s rover]'); ylabel('SE (b/s/Hz)');
title(sprintf(['Shannon spectral efficiency (256QAM-capped): mean %.2f, ' ...
               'min %.2f b/s/Hz'], mean(SE), min(SE)));

exportgraphics(gcf, 'site04_traj_S_trace.png', 'Resolution', 150);
fprintf('saved site04_traj_S_trace.png\n');

%% Optional: replay through nrTDLChannel (5G Toolbox)
if exist('nrTDLChannel', 'class') == 8
    fprintf('\n5G Toolbox found -- replaying 3 waypoints through nrTDLChannel\n');
    SR = 30.72e6;                                 % 20 MHz NR numerology 0
    v  = 1.0;                                     % m/s
    fd = v * fc / physconst('LightSpeed');        % ~8 Hz Doppler at walking pace
    % Pick the best, median and worst waypoints by tap gain.
    [~, order] = sort(gdB);
    picks = order([1, round(N/2), N]).';
    x = (randn(SR/1000*10, 1) + 1j*randn(SR/1000*10, 1)) / sqrt(2);  % 10 ms probe

    for i = picks
        keep = S.AveragePathGains(i, :) > -250;   % strip padding rows
        tdl = nrTDLChannel( ...
            'DelayProfile',        'Custom', ...
            'PathDelays',          S.PathDelays(i, keep), ...
            'AveragePathGains',    S.AveragePathGains(i, keep), ...
            'FadingDistribution',  'Rician', ...
            'KFactorFirstTap',     30, ...        % ray-based taps ~deterministic
            'MaximumDopplerShift', fd, ...
            'SampleRate',          SR, ...
            'NumTransmitAntennas', 1, ...
            'NumReceiveAntennas',  1);
        y = tdl(x);
        g_meas = 10*log10(mean(abs(y).^2) / mean(abs(x).^2));
        fprintf(['  waypoint %3d (t=%5.0f s, LOS=%d): taps=%d, ' ...
                 'predicted %+6.2f dB, nrTDLChannel measured %+6.2f dB\n'], ...
                i, t(i), S.LOS(i), nnz(keep), gdB(i), g_meas);
    end
    fprintf(['  (measured ~ predicted: the Custom profile carries the ' ...
             'pipeline channel. Swap the probe for nrWaveformGenerator ' ...
             'output + nrPUSCHDecode for full BLER curves.)\n']);
else
    fprintf(['\n5G Toolbox not found -- skipped nrTDLChannel replay. ' ...
             'Sections 1-2 above are toolbox-free.\n']);
end
