import React, { useState } from "react";
import AppShell from "../components/layout/AppShell";
import ResultStage from "../components/stage/ResultStage";
import SidePanel from "../components/panel/sidepanel/SidePanel";
import { useFileInput } from "../hooks/useFileInput";
import { useChatLogs } from "../hooks/useChatLogs";
import { useRecommend } from "../hooks/useRecommend";
import { createTurn } from "../utils/createTurn";
import { useInputOptions } from "../hooks/useInputOptions";
import { useAppData } from "../store/appDataStore.jsx";
const Home = () => {
  const { file, previewUrl, handleFile, setFile } = useFileInput();
  const { chatLogs, appendTurn, updateTurn } = useChatLogs();
  const { addHistoryTurn } = useAppData();
  const { requestRecommend } = useRecommend({
    updateTurn,
    onHistoryTurn: addHistoryTurn,
  });
  const [error, setError] = useState(null);

  const {
    textQuery,
    setTextQuery,
    category,
    setCategory,
    gender,
    setGender,
    reset,
  } = useInputOptions();
  const handleSubmit = async () => {
    if (!file) {
      setError({ code: "NO_FILE", message: "이미지를 업로드해주세요" });
      return;
    }
    const newTurn = createTurn({
      file,
      previewUrl,
      textQuery,
      category,
      gender,
    });
    appendTurn(newTurn);
    await requestRecommend({
      turnId: newTurn.id,
      file,
      textQuery,
      category,
      gender,
    });
    setFile(null);
    reset();
  };
  return (
    <>
      <AppShell
        left={<ResultStage chatLogs={chatLogs} />}
        right={
          <SidePanel
            file={file}
            error={error}
            previewUrl={previewUrl}
            onTextQuery={setTextQuery}
            textQuery={textQuery}
            onChangeCategory={setCategory}
            category={category}
            onChangeGender={setGender}
            gender={gender}
            onFile={handleFile}
            onSubmit={handleSubmit}
          />
        }
      />
    </>
  );
};
export default Home;
