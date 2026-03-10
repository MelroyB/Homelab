export function readCookie(name: string): string | null {
  const cookies = document.cookie.split(";").map((part) => part.trim());
  const hit = cookies.find((cookie) => cookie.startsWith(`${name}=`));
  if (!hit) {
    return null;
  }
  return decodeURIComponent(hit.slice(name.length + 1));
}
