def tabulate(table_data, headers=None, tablefmt=None):
    lines = []
    if headers:
        lines.append(' | '.join(headers))
    for row in table_data:
        lines.append(' | '.join(str(x) for x in row))
    return '\n'.join(lines)
