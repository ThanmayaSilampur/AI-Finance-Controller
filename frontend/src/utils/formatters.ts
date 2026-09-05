/**
 * Currency, number, and date formatters for financial data.
 */

export function formatCurrency(
  amount: number | string | null | undefined,
  currency: string = 'INR'
): string {
  if (amount === null || amount === undefined || isNaN(Number(amount))) {
    return '—';
  }

  const num = typeof amount === 'string' ? parseFloat(amount) : amount;
  const isNegative = num < 0;
  const absVal = Math.abs(num);

  const formatted = new Intl.NumberFormat('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(absVal);

  const symbol = currency === 'INR' ? '₹' : currency === 'USD' ? '$' : `${currency} `;
  return isNegative ? `-${symbol}${formatted}` : `${symbol}${formatted}`;
}

export function formatNumber(value: number | string | null | undefined): string {
  if (value === null || value === undefined || isNaN(Number(value))) {
    return '0';
  }
  const num = typeof value === 'string' ? parseFloat(value) : value;
  return new Intl.NumberFormat('en-IN').format(num);
}

export function formatPercent(value: number | string | null | undefined, decimals: number = 1): string {
  if (value === null || value === undefined || isNaN(Number(value))) {
    return '0.0%';
  }
  const num = typeof value === 'string' ? parseFloat(value) : value;
  return `${num.toFixed(decimals)}%`;
}

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '—';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return dateStr;
  }
}
