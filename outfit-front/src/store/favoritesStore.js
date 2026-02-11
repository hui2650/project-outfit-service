import React from "react";

const FavoritesContext = React.createContext(null);

const safeParse = (raw, fallback) => {
  try {
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
};

export const FavoritesProvider = ({ children }) => {
  const [favorites, setFavorites] = React.useState(() =>
    safeParse(localStorage.getItem("favorites"), []),
  );

  React.useEffect(() => {
    try {
      localStorage.setItem("favorites", JSON.stringify(favorites));
    } catch {}
  }, [favorites]);

  const isLiked = React.useCallback(
    (item) => favorites.some((x) => x.itemKey === item.itemKey),
    [favorites],
  );

  const toggleLike = React.useCallback((item) => {
    setFavorites((prev) => {
      const exists = prev.some((x) => x.itemKey === item.itemKey);
      return exists
        ? prev.filter((x) => x.itemKey !== item.itemKey)
        : [{ ...item, likedAt: Date.now() }, ...prev];
    });
  }, []);

  const value = React.useMemo(
    () => ({ favorites, setFavorites, isLiked, toggleLike }),
    [favorites, isLiked, toggleLike],
  );

  return (
    <FavoritesContext.Provider value={value}>
      {children}
    </FavoritesContext.Provider>
  );
};

export const useFavorites = () => {
  const ctx = React.useContext(FavoritesContext);
  if (!ctx)
    throw new Error("useFavorites must be used within FavoritesProvider");
  return ctx;
};
