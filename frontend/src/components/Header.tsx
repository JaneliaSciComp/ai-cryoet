import { useState } from "react";
import {
  AppBar,
  Box,
  IconButton,
  Menu,
  MenuItem,
  Toolbar,
  Typography,
  css,
  styled,
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import { CustomLink } from "./CustomLink";
import snowflakeLogo from "~/assets/snowflake-logo.svg";

const StyledCustomLink = styled(CustomLink)(
  ({ theme }) => css`
    color: ${theme.palette.common.white};
    font-weight: 500;
  `,
);

// The app name doubles as a "home" link, so style it like a heading but keep
// it a link for affordance + keyboard access.
const BrandLink = styled(CustomLink)(
  ({ theme }) => css`
    color: ${theme.palette.secondary.main};
    text-decoration: none;
    font-weight: 700;
  `,
);

// Links inside the mobile menu fill the whole MenuItem so the entire row is a
// click target, and inherit the menu's text color rather than link blue.
const MenuLink = styled(CustomLink)`
  display: block;
  width: 100%;
  color: inherit;
  text-decoration: none;
`;

export function Header() {
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const menuOpen = Boolean(anchorEl);
  const closeMenu = () => setAnchorEl(null);

  return (
    <Box>
      <AppBar position="static">
        <Toolbar sx={{ gap: 3 }}>
          <BrandLink
            to="/"
            sx={{ display: "flex", alignItems: "center", gap: 1 }}
          >
            <Box
              component="img"
              src={snowflakeLogo}
              alt=""
              sx={{ width: 36, height: 36, display: "block" }}
            />
            <Typography variant="h6" component="span" color="inherit">
              AI+CryoET Data Portal
            </Typography>
          </BrandLink>
          <Box sx={{ flexGrow: 1 }} />

          {/* Desktop / tablet: inline links. */}
          <Box sx={{ display: { xs: "none", md: "flex" }, gap: 3 }}>
            <StyledCustomLink to="/experimental">
              Experimental Data
            </StyledCustomLink>
            <StyledCustomLink to="/md-simulation">
              MD Simulations
            </StyledCustomLink>
            <StyledCustomLink to="/manage">Manage</StyledCustomLink>
          </Box>

          {/* Mobile: collapse the links into a hamburger menu. */}
          <Box sx={{ display: { xs: "flex", md: "none" } }}>
            <IconButton
              color="inherit"
              edge="end"
              aria-label="Open navigation menu"
              aria-controls={menuOpen ? "nav-menu" : undefined}
              aria-haspopup="true"
              aria-expanded={menuOpen ? "true" : undefined}
              onClick={(e) => setAnchorEl(e.currentTarget)}
            >
              <MenuIcon />
            </IconButton>
            <Menu
              id="nav-menu"
              anchorEl={anchorEl}
              open={menuOpen}
              onClose={closeMenu}
              anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
              transformOrigin={{ vertical: "top", horizontal: "right" }}
            >
              <MenuItem onClick={closeMenu}>
                <MenuLink to="/experimental">Experimental Data</MenuLink>
              </MenuItem>
              <MenuItem onClick={closeMenu}>
                <MenuLink to="/md-simulation">MD Simulations</MenuLink>
              </MenuItem>
              <MenuItem onClick={closeMenu}>
                <MenuLink to="/manage">Manage</MenuLink>
              </MenuItem>
            </Menu>
          </Box>
        </Toolbar>
      </AppBar>
    </Box>
  );
}
