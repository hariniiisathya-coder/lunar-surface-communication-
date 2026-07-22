%RUN_PUSCH_BLER  5G NR PUSCH BLER/throughput over lunar vs terrestrial channels.
%
%   Runs a single-layer PUSCH link-level loop (RV=0, no HARQ) over three
%   channels and sweeps SNR, producing BLER-vs-SNR and throughput curves:
%
%     1. Lunar LOS      — the two-ray tap from site04_traj_S.mat (sub-ns
%                         excess delay -> effectively one tap -> frequency
%                         FLAT), Rician, worst-case Ka Doppler (90 Hz).
%     2. Lunar NLOS     — a 2-edge crater-diffraction profile [0, 200 ns],
%                         Rayleigh: the largest delay spread this terrain
%                         model produces.
%     3. Terrestrial    — TDL-C, 300 ns delay spread (3GPP TR 38.901), the
%                         standard urban contrast.
%
%   Result: the lunar surface channel is near-AWGN (no frequency selectivity,
%   negligible Doppler across UHF->Ka); the terrestrial TDL-C shows the
%   familiar selectivity penalty. Channels are power-normalised here
%   (NormalizePathGains=true) because SNR is the swept variable — the OPPOSITE
%   of run_nrtdl_demo.m, where absolute two-ray gain was the point.
%
%   Run from this folder:  >> run_pusch_bler
%   Bounded for a quick run; raise NUM_SLOTS / add SNR points for smooth tails.

if exist('nrCarrierConfig', 'class') ~= 8
    error('run_pusch_bler needs the 5G Toolbox.');
end
rng(211);

%% Link configuration — 20 MHz, SCS 30 kHz (numerology 1)
carrier = nrCarrierConfig;
carrier.NSizeGrid = 51;
carrier.SubcarrierSpacing = 30;

pusch = nrPUSCHConfig;
pusch.Modulation = '16QAM';
pusch.NumLayers  = 1;
pusch.PRBSet     = 0:carrier.NSizeGrid-1;
pusch.DMRS.DMRSAdditionalPosition = 1;
targetCodeRate = 490/1024;

encodeULSCH = nrULSCH;
decodeULSCH = nrULSCHDecoder;
decodeULSCH.LDPCDecodingAlgorithm = 'Normalized min-sum';

ofdmInfo = nrOFDMInfo(carrier);
SR = ofdmInfo.SampleRate;

fcKa = 27e9; v = 1.0;
fdKa = v * fcKa / physconst('LightSpeed');   % 90 Hz — worst lunar Doppler

% Authentic lunar-LOS tap from the exported traverse (median waypoint).
S = load('site04_traj_S.mat');
[~, ord] = sort(S.GainMagnitude_dB(:));
wp = ord(round(numel(ord)/2));
losDelays = S.PathDelays(wp, S.AveragePathGains(wp,:) > -250);

makeChannel = containers.Map();
makeChannel('Lunar LOS (2-ray, flat)') = @() nrTDLChannel( ...
    'DelayProfile','Custom','PathDelays',losDelays, ...
    'AveragePathGains',zeros(1,numel(losDelays)), ...
    'FadingDistribution','Rician','KFactorFirstTap',13, ...
    'MaximumDopplerShift',fdKa,'SampleRate',SR);
makeChannel('Lunar NLOS (2-edge, 200 ns)') = @() nrTDLChannel( ...
    'DelayProfile','Custom','PathDelays',[0 200e-9], ...
    'AveragePathGains',[0 -3],'FadingDistribution','Rayleigh', ...
    'MaximumDopplerShift',fdKa,'SampleRate',SR);
makeChannel('Terrestrial TDL-C 300 ns') = @() nrTDLChannel( ...
    'DelayProfile','TDL-C','DelaySpread',300e-9, ...
    'MaximumDopplerShift',fdKa,'SampleRate',SR);

SNRdB = 2:1.5:14;
NUM_SLOTS = 120;
names = keys(makeChannel);
BLER = zeros(numel(names), numel(SNRdB));
TPUT = zeros(numel(names), numel(SNRdB));

%% Sweep
for c = 1:numel(names)
    make = makeChannel(names{c});
    for s = 1:numel(SNRdB)
        channel = make();
        chInfo = info(channel);
        pathFilters = getPathFilters(channel);
        maxChDelay = ceil(max(chInfo.PathDelays*SR)) + chInfo.ChannelFilterDelay;
        nErr = 0; nBlk = 0; okBits = 0;
        for nslot = 0:NUM_SLOTS-1
            carrier.NSlot = nslot;
            [puschInd, puschInfo] = nrPUSCHIndices(carrier, pusch);
            trBlkLen = nrTBS(pusch.Modulation, pusch.NumLayers, ...
                numel(pusch.PRBSet), puschInfo.NREPerPRB, targetCodeRate);
            trBlk = randi([0 1], trBlkLen, 1);
            setTransportBlock(encodeULSCH, trBlk);
            cw = encodeULSCH(pusch.Modulation, pusch.NumLayers, puschInfo.G, 0);

            sym = nrPUSCH(carrier, pusch, cw);
            grid = nrResourceGrid(carrier, 1);
            grid(puschInd) = sym;
            dmrsSym = nrPUSCHDMRS(carrier, pusch);
            dmrsInd = nrPUSCHDMRSIndices(carrier, pusch);
            grid(dmrsInd) = dmrsSym;

            tx = nrOFDMModulate(carrier, grid);
            tx = [tx; zeros(maxChDelay, size(tx,2))]; %#ok<AGROW>
            [rx, pathG] = channel(tx);

            % noise scaled to the swept SNR (per RE, accounting for FFT gain)
            SNR = 10^(SNRdB(s)/10);
            N0 = 1/sqrt(2 * ofdmInfo.Nfft * SNR);
            rx = rx + N0*complex(randn(size(rx)), randn(size(rx)));

            % perfect timing from the channel path gains (offset comp.)
            offset = nrPerfectTimingEstimate(pathG, pathFilters);
            rx = rx(1+offset:end, :);

            rxGrid = nrOFDMDemodulate(carrier, rx);
            [H, nVar] = nrChannelEstimate(carrier, rxGrid, dmrsInd, dmrsSym);
            [puschRx, puschH] = nrExtractResources(puschInd, rxGrid, H);
            eq = nrEqualizeMMSE(puschRx, puschH, nVar);
            llr = nrPUSCHDecode(carrier, pusch, eq, nVar);

            % reset the decoder soft buffer each slot: RV=0 fresh transmission,
            % no HARQ combining across (independent) transport blocks. Omitting
            % this makes every block fail — the decoder combines mismatched TBs.
            reset(decodeULSCH);
            decodeULSCH.TransportBlockLength = trBlkLen;
            [~, blkerr] = decodeULSCH(llr, pusch.Modulation, ...
                pusch.NumLayers, 0);
            nErr = nErr + blkerr; nBlk = nBlk + 1;
            if ~blkerr, okBits = okBits + trBlkLen; end
        end
        BLER(c,s) = nErr / nBlk;
        slot_s = 1e-3 / (carrier.SubcarrierSpacing / 15);   % 0.5 ms @ SCS 30
        TPUT(c,s) = okBits / (NUM_SLOTS * slot_s) / 1e6;    % Mbps
        fprintf('%-28s SNR %+5.1f dB: BLER %.3f, tput %.1f Mbps\n', ...
            names{c}, SNRdB(s), BLER(c,s), TPUT(c,s));
    end
end

%% Plot
figure('Name','PUSCH BLER — lunar vs terrestrial','Position',[80 80 1000 420]);
subplot(1,2,1);
mk = {'-o','-s','-^'};
for c = 1:numel(names)
    semilogy(SNRdB, max(BLER(c,:),1e-3), mk{c}, 'LineWidth',1.3); hold on;
end
grid on; ylim([1e-3 1]); xlabel('SNR (dB)'); ylabel('BLER');
legend(names,'Location','southwest','Interpreter','none');
title('PUSCH BLER — 16QAM R=0.48, 20 MHz');

subplot(1,2,2);
for c = 1:numel(names)
    plot(SNRdB, TPUT(c,:), mk{c}, 'LineWidth',1.3); hold on;
end
grid on; xlabel('SNR (dB)'); ylabel('throughput (Mbps)');
legend(names,'Location','southeast','Interpreter','none');
title('PUSCH throughput');
exportgraphics(gcf, 'pusch_bler_lunar_vs_terrestrial.png', 'Resolution', 150);
fprintf('saved pusch_bler_lunar_vs_terrestrial.png\n');
