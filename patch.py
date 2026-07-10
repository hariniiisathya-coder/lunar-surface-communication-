import re, pathlib
p = pathlib.Path("lunarcomms/regolith/dielectric.py")
lines = p.read_text().splitlines(keepends=True)

impls = {
    "permittivity": ["    return 1.919 ** rho\n"],
    "loss_tangent": ["    return 10 ** (0.312 * rho - 2.636) * freq_ghz ** 0.278\n"],
    "complex_permittivity": ["    return permittivity(rho) * (1 - 1j * loss_tangent(rho, freq_ghz))\n"],
    "fresnel_coefficients": [
        "    eps_c = complex_permittivity(rho, freq_ghz)\n",
        "    theta = np.asarray(theta_rad, dtype=float)\n",
        "    root = np.sqrt(eps_c - np.cos(theta) ** 2)\n",
        "    gamma_v = (eps_c * np.sin(theta) - root) / (eps_c * np.sin(theta) + root)\n",
        "    gamma_h = (np.sin(theta) - root) / (np.sin(theta) + root)\n",
        "    return gamma_v, gamma_h\n",
    ],
}

out = []
i = 0
n = len(lines)
while i < n:
    line = lines[i]
    m = re.match(r'def (\w+)\(', line)
    if m and m.group(1) in impls:
        name = m.group(1)
        out.append(line)
        i += 1
        while i < n and not re.search(r'\):\s*$|->.*:\s*$', lines[i]):
            out.append(lines[i]); i += 1
        if i < n:
            out.append(lines[i]); i += 1
        if i < n and lines[i].lstrip().startswith('"""'):
            out.append(lines[i])
            if lines[i].strip().count('"""') < 2:
                i += 1
                while i < n and '"""' not in lines[i]:
                    out.append(lines[i]); i += 1
                if i < n:
                    out.append(lines[i]); i += 1
            else:
                i += 1
        while i < n and not lines[i].startswith("def "):
            i += 1
        out.extend(impls[name])
        out.append("\n")
    else:
        out.append(line); i += 1

p.write_text("".join(out))
print("Rewrote all four functions.")
