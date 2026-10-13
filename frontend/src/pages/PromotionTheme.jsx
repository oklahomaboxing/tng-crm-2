import React from "react";
import { ThemeProvider, createTheme } from "@mui/material/styles";
import "./promotion.css";
const theme = createTheme({
  palette: { mode: "light", primary: { main: "#d71920" }, background: { default: "#f5f6f8", paper: "#ffffff" }, text: { primary: "#17202c", secondary: "#606b7b" }, divider: "#e1e5eb" },
  typography: { fontFamily: 'Inter, "Segoe UI", sans-serif', h4: { fontWeight: 850, letterSpacing: "-.035em" }, h5: { fontWeight: 850, letterSpacing: "-.025em" }, h6: { fontWeight: 800 }, button: { textTransform: "none", fontWeight: 750 } },
  shape: { borderRadius: 12 },
  components: { MuiCard: { styleOverrides: { root: { border: "1px solid #e1e5eb", boxShadow: "0 4px 20px #17202c04" } } }, MuiButton: { defaultProps: { disableElevation: true }, styleOverrides: { root: { minHeight: 40 }, contained: { padding: "10px 20px" } } }, MuiTableCell: { styleOverrides: { head: { background: "#f6f8fa", fontWeight: 800, fontSize: 12 }, root: { borderColor: "#edf0f3" } } } },
});
export default function PromotionTheme({ children }) { return <ThemeProvider theme={theme}><div className="promotion-scope">{children}</div></ThemeProvider>; }
