%RUN_AMC_CURVE  Measured link-adaptation (AMC) throughput vs SNR curve.
%
%   Sweeps a set of NR MCS (QPSK -> 256QAM) over the lunar LOS channel (the
%   two-ray tap from site04_traj_S.mat, near-AWGN) and, at each SNR, records
%   the best achievable PUSCH throughput = max over MCS of
%   SE * B * (1 - BLER), i.e. the AMC envelope a real scheduler would ride.
%
%   Writes matlab/amc_throughput_curve.csv (SNR_dB, throughput_Mbps) — the
%   measured lookup that analysis/band_comparison_maps.py uses to turn its
%   per-pixel SNR maps into MCS-accurate throughput (instead of Shannon).
%
%   Run from this folder:  >> run_amc_curve
%
%   This is the same validated PUSCH chain as run_pusch_bler.m (nrULSCH /
%   nrPUSCH / nrChannelEstimate / nrEqualizeMMSE / nrULSCHDecoder,
%   reset(decodeULSCH) per slot, NormalizePathGains=true since SNR is swept).

if exist('nrCarrierConfig', 'class') ~= 8
    error('run_amc_curve needs the 5G Toolbox.');
end
rng(707);

carrier = nrCarrierConfig;
carrier.NSizeGrid = 51;
carrier.SubcarrierSpacing = 30;
ofdmInfo = nrOFDMInfo(carrier);
SR = ofdmInfo.SampleRate;
slot_s = 1e-3 / (carrier.SubcarrierSpacing / 15);   % 0.5 ms @ SCS 30
B_Hz = carrier.NSizeGrid * 12 * carrier.SubcarrierSpacing * 1e3;  % ~18.4 MHz used

% Representative NR MCS ladder (modulation, target code rate).
MCS = { ...
    'QPSK',   120/1024; ...
    'QPSK',   449/1024; ...
    '16QAM',  490/1024; ...
    '16QAM',  616/1024; ...
    '64QAM',  567/1024; ...
    '64QAM',  754/1024; ...
    '256QAM', 682.5/1024; ...
    '256QAM', 895/1024 };
bitsPerSym = containers.Map({'QPSK','16QAM','64QAM','256QAM'}, {2,4,6,8});

% Lunar LOS channel (median waypoint tap), Rician, worst-case Ka Doppler.
S = load('site04_traj_S.mat');
[~, ord] = sort(S.GainMagnitude_dB(:));
wp = ord(round(numel(ord)/2));
losDelays = S.PathDelays(wp, S.AveragePathGains(wp,:) > -250);
fdKa = 1.0 * 27e9 / physconst('LightSpeed');
makeCh = @() nrTDLChannel('DelayProfile','Custom','PathDelays',losDelays, ...
    'AveragePathGains',zeros(1,numel(losDelays)),'NormalizePathGains',true, ...
    'FadingDistribution','Rician','KFactorFirstTap',13, ...
    'MaximumDopplerShift',fdKa,'SampleRate',SR);

SNRdB = -4:2:30;
NUM_SLOTS = 60;
tputMCS = zeros(size(MCS,1), numel(SNRdB));

encodeULSCH = nrULSCH;
decodeULSCH = nrULSCHDecoder;
decodeULSCH.LDPCDecodingAlgorithm = 'Normalized min-sum';

for m = 1:size(MCS,1)
    modulation = MCS{m,1};
    R = MCS{m,2};
    pusch = nrPUSCHConfig;
    pusch.Modulation = modulation;
    pusch.NumLayers  = 1;
    pusch.PRBSet     = 0:carrier.NSizeGrid-1;
    pusch.DMRS.DMRSAdditionalPosition = 1;
    for s = 1:numel(SNRdB)
        channel = makeCh();
        chInfo = info(channel);
        pathFilters = getPathFilters(channel);
        maxChDelay = ceil(max(chInfo.PathDelays*SR)) + chInfo.ChannelFilterDelay;
        nErr = 0; nBlk = 0; okBits = 0;
        for nslot = 0:NUM_SLOTS-1
            carrier.NSlot = nslot;
            [puschInd, puschInfo] = nrPUSCHIndices(carrier, pusch);
            trBlkLen = nrTBS(modulation, 1, numel(pusch.PRBSet), ...
                puschInfo.NREPerPRB, R);
            trBlk = randi([0 1], trBlkLen, 1);
            setTransportBlock(encodeULSCH, trBlk);
            cw = encodeULSCH(modulation, 1, puschInfo.G, 0);
            sym = nrPUSCH(carrier, pusch, cw);
            grid = nrResourceGrid(carrier, 1);
            grid(puschInd) = sym;
            dmrsSym = nrPUSCHDMRS(carrier, pusch);
            grid(nrPUSCHDMRSIndices(carrier, pusch)) = dmrsSym;
            tx = nrOFDMModulate(carrier, grid);
            tx = [tx; zeros(maxChDelay, 1)]; %#ok<AGROW>
            [rx, pathG] = channel(tx);
            N0 = 1/sqrt(2 * ofdmInfo.Nfft * 10^(SNRdB(s)/10));
            rx = rx + N0*complex(randn(size(rx)), randn(size(rx)));
            offset = nrPerfectTimingEstimate(pathG, pathFilters);
            rx = rx(1+offset:end, :);
            rxGrid = nrOFDMDemodulate(carrier, rx);
            [H, nVar] = nrChannelEstimate(carrier, rxGrid, ...
                nrPUSCHDMRSIndices(carrier, pusch), dmrsSym);
            [puschRx, puschH] = nrExtractResources(puschInd, rxGrid, H);
            eq = nrEqualizeMMSE(puschRx, puschH, nVar);
            llr = nrPUSCHDecode(carrier, pusch, eq, nVar);
            reset(decodeULSCH);
            decodeULSCH.TransportBlockLength = trBlkLen;
            [~, blkerr] = decodeULSCH(llr, modulation, 1, 0);
            nErr = nErr + blkerr; nBlk = nBlk + 1;
            if ~blkerr, okBits = okBits + trBlkLen; end
        end
        tputMCS(m,s) = okBits / (NUM_SLOTS * slot_s) / 1e6;   % Mbps
    end
    fprintf('MCS %-6s R=%.2f  peak %.1f Mbps\n', modulation, R, max(tputMCS(m,:)));
end

% AMC envelope: best MCS at each SNR.
tputEnv = max(tputMCS, [], 1);

writematrix([SNRdB(:) tputEnv(:)], 'amc_throughput_curve.csv');
fprintf('saved amc_throughput_curve.csv (%d points, peak %.1f Mbps)\n', ...
    numel(SNRdB), max(tputEnv));

figure('Name','AMC throughput curve','Position',[80 80 720 460]);
plot(SNRdB, tputMCS.', ':', 'LineWidth', 0.8); hold on;
plot(SNRdB, tputEnv, 'k-', 'LineWidth', 2.0);
grid on; xlabel('SNR (dB)'); ylabel('throughput (Mbps)');
legend([compose('%s R=%.2f', string(MCS(:,1)), cell2mat(MCS(:,2))); ...
    "AMC envelope"], 'Location','northwest','Interpreter','none','FontSize',7);
title('Measured PUSCH link-adaptation curve, lunar LOS channel (18.4 MHz)');
exportgraphics(gcf, 'amc_throughput_curve.png', 'Resolution', 150);
fprintf('saved amc_throughput_curve.png\n');
