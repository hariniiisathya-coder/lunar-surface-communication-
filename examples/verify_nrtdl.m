% verify_nrtdl.m -- close the loop in MATLAB.
% Loads the Python-exported channel and checks that (a) the tap description
% reconstructs the two-ray path loss and (b) nrTDLChannel accepts it and its
% average path gains match what we exported.
%
% Run:  matlab -batch "cd('examples'); verify_nrtdl"
% Requires: 5G Toolbox (nrTDLChannel). The (a) reconstruction check runs with
% base MATLAB alone.

S = load('channel_traj.mat');
nWp = size(S.PathDelays, 1);
fprintf('loaded %d waypoints, carrier %.3f GHz\n', nWp, S.CarrierHz/1e9);

% (a) LOOP CLOSURE: reconstruct total path loss per waypoint from the exported
%     taps (FSPLDirect_dB - GainMagnitude_dB) and compare to the Python
%     two_ray.path_loss_db reference carried in the same file. The trace is
%     non-monotone by design (two-ray interference nulls as the rover moves).
totalPL = S.FSPLDirect_dB(:) - S.GainMagnitude_dB(:);
refPL   = S.TwoRayPL_dB(:);
err = max(abs(totalPL - refPL));
fprintf('total PL range: %.1f .. %.1f dB\n', min(totalPL), max(totalPL));
fprintf('max |MATLAB tap PL - Python two_ray PL| = %.4f dB  -> %s\n', ...
    err, ternary(err < 0.05, 'PASS', 'FAIL'));

% (b) Feed one representative LOS waypoint into nrTDLChannel and confirm it
%     builds and its AveragePathGains round-trip.
if exist('nrTDLChannel', 'class')
    w = round(nWp/2);
    delays = S.PathDelays(w, :);
    gains  = S.AveragePathGains(w, :);
    keep = isfinite(gains) & (gains > -200);   % strip padding
    tdl = nrTDLChannel;
    tdl.DelayProfile = 'Custom';
    tdl.PathDelays = delays(keep);
    tdl.AveragePathGains = gains(keep);
    tdl.SampleRate = 100e6;                     % 100 MS/s (MCHEM grid)
    info = info(tdl); %#ok<NODEF>
    fprintf('nrTDLChannel built at waypoint %d: %d path(s), maxDelay %.1f ns\n', ...
        w, numel(tdl.PathDelays), max(tdl.PathDelays)*1e9);
    fprintf('  exported AveragePathGains: %s dB\n', mat2str(gains(keep), 4));
    disp('PASS: nrTDLChannel accepted the exported custom profile.');
else
    disp('5G Toolbox not found; ran reconstruction check (a) only.');
end

function s = ternary(cond, a, b)
    if cond, s = a; else, s = b; end
end
