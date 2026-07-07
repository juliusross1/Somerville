# Solve:
# 94α + β = a
# 100α + β = u
# 114α + β = b

u = float(input("Enter u: "))
b = float(input("Enter b: "))

# Solve for alpha and beta
alpha = (b - u) / (114 - 100)   # = (b - u) / 14
beta = u - 100 * alpha

# Compute a
a = 94 * alpha + beta

print()
print(f"alpha = {alpha:.10f}")
print(f"beta  = {beta:.10f}")
print(f"a     = {a:.10f}")