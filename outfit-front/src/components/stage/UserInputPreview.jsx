import React from "react";
import ChatPreview from "./ChatPreview";

const UserInputPreview = ({ previewUrl, textQuery }) => {
  return (
    <>
      <ChatPreview previewUrl={previewUrl} textQuery={textQuery} />
    </>
  );
};

export default UserInputPreview;
