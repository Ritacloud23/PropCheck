import { MessageCircle, Phone } from "lucide-react";

import { formatNgPhone } from "@/lib/format";
import { waLink } from "@/lib/whatsapp";

import { buttonClass } from "./ui";

/** Renders nothing unless the API returned a number (it only does so with the agent's consent). */
export function WhatsAppButton({
  number,
  message,
  className,
}: {
  number: string | null;
  message: string;
  className?: string;
}) {
  const href = waLink(number, message);
  if (!href) return null;
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className={buttonClass("whatsapp", "md", className)}>
      <MessageCircle className="size-4" aria-hidden /> WhatsApp
    </a>
  );
}

export function CallButton({ number, className }: { number: string | null; className?: string }) {
  if (!number) return null;
  return (
    <a href={`tel:${number}`} className={buttonClass("secondary", "md", className)}>
      <Phone className="size-4" aria-hidden /> {formatNgPhone(number)}
    </a>
  );
}
