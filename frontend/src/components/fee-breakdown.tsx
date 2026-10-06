import { formatNaira } from "@/lib/format";
import type { Fees } from "@/lib/types";

export function FeeBreakdown({ fees }: { fees: Fees }) {
  const rows: [string, number, string | null][] = [
    ["Annual rent", fees.rent_amount, null],
    ["Agency fee", fees.agency_fee, null],
    ["Legal / agreement fee", fees.legal_fee, null],
    ["Caution deposit (refundable)", fees.caution_fee, null],
    ["Other fees", fees.other_fees, fees.other_fees_description],
  ];
  return (
    <div>
      <dl className="divide-y divide-slate-100">
        {rows.map(([label, amount, note]) => (
          <div key={label} className="flex justify-between gap-4 py-2.5 text-sm">
            <dt className="text-slate-600">
              {label}
              {note && <span className="block text-xs text-slate-400">{note}</span>}
            </dt>
            <dd className="font-medium tabular-nums text-slate-900">{formatNaira(amount)}</dd>
          </div>
        ))}
      </dl>
      <div className="mt-2 flex items-baseline justify-between rounded-lg bg-slate-900 px-4 py-3 text-white">
        <span className="text-sm font-medium">Total move-in cost</span>
        <span className="text-lg font-bold tabular-nums" data-testid="fee-total">
          {formatNaira(fees.total_move_in_cost)}
        </span>
      </div>
      <p className="mt-2 text-xs text-slate-500">
        PropCheck calculates the total from the fees above. Ask for a written breakdown before paying anything.
      </p>
    </div>
  );
}
