import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer disabled:pointer-events-none disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600",
  {
    variants: {
      variant: {
        default: "bg-teal-700 text-white hover:bg-teal-800 shadow-2xs",
        outline: "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 hover:text-slate-900 hover:border-slate-300 shadow-2xs",
        ghost: "text-slate-700 hover:bg-slate-100 hover:text-slate-900",
        success: "bg-emerald-700 text-white hover:bg-emerald-800 shadow-2xs",
        danger: "border border-rose-200 bg-rose-50 text-rose-800 hover:bg-rose-100/80 shadow-2xs",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-8 px-3 text-xs",
        lg: "h-11 px-5 text-sm",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants>;

export function Button({ className, variant, size, ...props }: ButtonProps) {
  return <button className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}

