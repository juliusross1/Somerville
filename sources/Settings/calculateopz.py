FACTOR_1 = 0.8
FACTOR_2 = 0.6

points = [
    (5, 5),
    (200, 6),
    (325, 7),
    (400, 8),
    (550, 12),
    (640, 16),
    (700, 21),
    (800, 32),
    (860, 41),
    (900, 38),
    (980, 72),
    (1020, 96),
    (1200, 1200),
]


def piecewise_value(x):
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]

        if x1 <= x <= x2:
            t = (x - x1) / (x2 - x1)
            return y1 + t * (y2 - y1)

    raise ValueError("x is outside the given range.")


def inverse_piecewise(y_target):
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]

        if min(y1, y2) <= y_target <= max(y1, y2):
            t = (y_target - y1) / (y2 - y1)
            return x1 + t * (x2 - x1)

    raise ValueError("target y is outside the given range.")


x = float(input("Enter x: "))

y = piecewise_value(x)

target_y_1 = FACTOR_1 * y
target_y_2 = FACTOR_2 * y

x_1 = inverse_piecewise(target_y_1)
x_2 = inverse_piecewise(target_y_2)

print(f"x = {x}")
print(f"y = {y}")

print(f"{FACTOR_1} * y = {target_y_1} gives x = {x_1}")
print(f"{FACTOR_2} * y = {target_y_2} gives x = {x_2}")