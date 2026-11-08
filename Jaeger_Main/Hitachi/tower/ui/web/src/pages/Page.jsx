import { Topbar } from "../components/Layout.jsx";

// Every page: the title bar, then its content.
export function Page({ title, subtitle, trail, showRefresh = true, children }) {
  return (
    <>
      <Topbar title={title} subtitle={subtitle} trail={trail} showRefresh={showRefresh} />
      <div>{children}</div>
    </>
  );
}
