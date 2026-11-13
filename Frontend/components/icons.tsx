import type { SVGProps } from "react";

// Hairline 1.6px stroke icons, sized by the parent via className (default 20px).
type IconProps = SVGProps<SVGSVGElement>;

function Icon({ children, className = "size-5", ...props }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className={className} {...props}>
      {children}
    </svg>
  );
}

export const AnalyzeIcon = (p: IconProps) => <Icon {...p}><path d="M3 15l4-5 3 3 5-7" /><circle cx="16.5" cy="15.5" r="3" /><path d="M18.7 17.7L21 20" /></Icon>;
export const HistoryIcon = (p: IconProps) => <Icon {...p}><path d="M3 6.5C5.5 5 8.5 5 11 6.5V19c-2.5-1.5-5.5-1.5-8 0z" /><path d="M11 6.5c2.5-1.5 5.5-1.5 8 0" /><path d="M15 4v10l2-1.5 2 1.5V4" /></Icon>;
export const AboutIcon = (p: IconProps) => <Icon {...p}><path d="M2.5 6c3-1.5 6-1.5 9.5 0v13c-3.5-1.5-6.5-1.5-9.5 0z" /><path d="M12 6c3.5-1.5 6.5-1.5 9.5 0v13c-3-1.5-6-1.5-9.5 0" /><path d="M14.5 10h4.5M14.5 13h4.5" /></Icon>;
export const TextIcon = (p: IconProps) => <Icon {...p}><path d="M4 7h16M4 12h16M4 17h10" /></Icon>;
export const ThreadIcon = (p: IconProps) => <Icon {...p}><path d="M4 5h11v8H8l-4 3z" /><path d="M15 9h5v8l-3-2.5h-6V13" /></Icon>;
export const TableIcon = (p: IconProps) => <Icon {...p}><rect x="4" y="4" width="16" height="16" rx="1.5" /><path d="M4 9h16M10 9v11" /></Icon>;
export const SearchIcon = (p: IconProps) => <Icon {...p}><circle cx="11" cy="11" r="6" /><path d="M20 20l-4.5-4.5" /></Icon>;
export const ArrowRightIcon = (p: IconProps) => <Icon {...p}><path d="M5 12h14M13 6l6 6-6 6" /></Icon>;
export const ArrowLeftIcon = (p: IconProps) => <Icon {...p}><path d="M19 12H5M11 6l-6 6 6 6" /></Icon>;
export const UploadIcon = (p: IconProps) => <Icon {...p}><path d="M7 18a4.5 4.5 0 01-.6-8.96A6 6 0 0118 9a4 4 0 01-.5 8" /><path d="M12 12v8M9 15l3-3 3 3" /></Icon>;
export const FileIcon = (p: IconProps) => <Icon {...p}><path d="M7 3h7l5 5v13H7z" /><path d="M14 3v5h5M10 13h6M10 17h6" /></Icon>;
export const CloseIcon = (p: IconProps) => <Icon {...p}><path d="M6 6l12 12M18 6L6 18" /></Icon>;
export const SwapIcon = (p: IconProps) => <Icon {...p}><path d="M4 9h14l-3-3M20 15H6l3 3" /></Icon>;
export const InfoIcon = (p: IconProps) => <Icon {...p}><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8h.01" /></Icon>;
export const CheckCircleIcon = (p: IconProps) => <Icon {...p}><circle cx="12" cy="12" r="9" /><path d="M8.5 12.5l2.5 2.5 4.5-5" /></Icon>;
export const AlertIcon = (p: IconProps) => <Icon {...p}><circle cx="12" cy="12" r="9" /><path d="M12 7.5v5.5M12 16.5h.01" /></Icon>;
export const LogoutIcon = (p: IconProps) => <Icon {...p}><path d="M10 4H5v16h5" /><path d="M14 8l4 4-4 4M18 12H9" /></Icon>;
export const UserIcon = (p: IconProps) => <Icon {...p}><circle cx="12" cy="8.5" r="3.5" /><path d="M5 20c1-3.5 3.8-5 7-5s6 1.5 7 5" /></Icon>;
export const RefreshIcon = (p: IconProps) => <Icon {...p}><path d="M20 11a8 8 0 00-14.5-4.5L4 8" /><path d="M4 4v4h4" /><path d="M4 13a8 8 0 0014.5 4.5L20 16" /><path d="M20 20v-4h-4" /></Icon>;
export const DownloadIcon = (p: IconProps) => <Icon {...p}><path d="M12 4v11M7 10l5 5 5-5M5 20h14" /></Icon>;
export const PlusIcon = (p: IconProps) => <Icon {...p}><path d="M12 5v14M5 12h14" /></Icon>;
export const LightbulbIcon = (p: IconProps) => <Icon {...p}><path d="M9 18h6M10 21h4" /><path d="M12 3a6 6 0 00-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0012 3z" /></Icon>;
export const AtIcon = (p: IconProps) => <Icon {...p}><circle cx="12" cy="12" r="3.5" /><path d="M15.5 12v1.5a2.5 2.5 0 005 0V12a8.5 8.5 0 10-3.3 6.7" /></Icon>;
export const LayersIcon = (p: IconProps) => <Icon {...p}><rect x="4" y="4" width="16" height="16" rx="1.5" /><path d="M8 8h3v3H8zM13 8h3v3h-3zM8 13h3v3H8zM13 13h3v3h-3z" /></Icon>;
