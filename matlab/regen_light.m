% regen_light.m — regenerate the link-level figures with a LIGHT theme for
% print (R2026a defaults figures to a dark theme). Forces the light graphics
% theme, then re-runs the three plotting scripts. Run from the matlab/ folder.

try
    s = settings;
    s.matlab.appearance.figure.GraphicsTheme.TemporaryValue = "light";
    fprintf('Forced light graphics theme.\n');
catch ME
    fprintf('Could not set theme via settings (%s); trying groot defaults.\n', ME.message);
    set(groot, 'defaultFigureColor', 'w');
    set(groot, 'defaultAxesColor', 'w');
    set(groot, 'defaultAxesXColor', 'k');
    set(groot, 'defaultAxesYColor', 'k');
end

has5g = exist('nrTDLChannel', 'class') == 8;
fprintf('5G Toolbox present: %d\n', has5g);

fprintf('\n=== run_nrtdl_demo (trajectory trace, toolbox-free) ===\n');
run('run_nrtdl_demo.m'); close all;

if has5g
    fprintf('\n=== run_pusch_bler (BLER/throughput) ===\n');
    run('run_pusch_bler.m'); close all;
    fprintf('\n=== run_amc_curve (AMC envelope) ===\n');
    run('run_amc_curve.m'); close all;
else
    fprintf('\n5G Toolbox missing -- skipping BLER + AMC.\n');
end

fprintf('\nALL DONE regen_light\n');
