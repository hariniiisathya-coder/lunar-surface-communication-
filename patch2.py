import pathlib

p = pathlib.Path("lunarcomms/regolith/dielectric.py")
lines = p.read_text().splitlines(keepends=True)

bodies = {
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
current = None       # name of function we're inside
i = 0
n = len(lines)
while i < n:
    line = lines[i]
    stripped = line.strip()

    # Track which function we're in
    if stripped.startswith("def "):
        name = stripped[4:].split("(")[0]
        current = name

    # If this line starts a raise NotImplementedError block in a target function
    if stripped.startswith("raise NotImplementedError(") and current in bodies:
        # write the replacement body
        out.extend(bodies[current])
        # skip lines until we pass the closing ')' of the raise(...)
        i += 1
        while i < n and lines[i].strip() != ")":
            i += 1
        i += 1  # skip the ')' line itself
        current = None  # done with this function
        continue

    out.append(line)
    i += 1

p.write_text("".join(out))
print("Patched. Check below for remaining stubs:")
