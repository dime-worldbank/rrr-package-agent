# ============================================================
# Variable Inventory Script
# Reads all datasets in a directory and outputs a CSV with
# dataset names, variable count, and variable lists.
#
# INPUT:  Set `data_dir` below to your data folder path
# OUTPUT: variable_inventory.csv saved in the same directory
# ============================================================

# ----- ONLY LINE TO CHANGE -----
data_dir <- "PTH HERE"
# --------------------------------

# Supported file types and their readers
supported_ext <- c("csv", "dta", "rds", "rdata", "xlsx", "xls", "sav", "tsv")

# Install missing packages quietly
required_pkgs <- c("haven", "readxl")
for (pkg in required_pkgs) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    install.packages(pkg, quiet = TRUE)
  }
}

library(haven)
library(readxl)

# ---- Helper: read a file based on extension ----
read_dataset <- function(filepath) {
  ext <- tolower(tools::file_ext(filepath))
  tryCatch({
    switch(ext,
      csv   = read.csv(filepath, nrows = 1, check.names = FALSE),
      tsv   = read.delim(filepath, nrows = 1, check.names = FALSE),
      dta   = haven::read_dta(filepath, n_max = 1),
      sav   = haven::read_sav(filepath, n_max = 1),
      rds   = readRDS(filepath),
      rdata = { e <- new.env(); load(filepath, envir = e); get(ls(e)[1], envir = e) },
      xlsx  = readxl::read_excel(filepath, n_max = 1),
      xls   = readxl::read_excel(filepath, n_max = 1),
      NULL
    )
  }, error = function(e) NULL)
}

# ---- Discover all supported files ----
all_files <- list.files(
  path       = data_dir,
  full.names = TRUE,
  recursive  = TRUE  # change to TRUE to search subdirectories
)

target_files <- all_files[
  tolower(tools::file_ext(all_files)) %in% supported_ext
]

if (length(target_files) == 0) {
  stop("No supported dataset files found in: ", data_dir)
}

cat("Found", length(target_files), "dataset(s). Processing...\n\n")

# ---- Process each file ----
results <- vector("list", length(target_files))

for (i in seq_along(target_files)) {
  fp       <- target_files[i]
  filename <- basename(fp)
  cat(sprintf("[%d/%d] %s ... ", i, length(target_files), filename))

  df <- read_dataset(fp)

  if (is.null(df) || !is.data.frame(df)) {
    cat("SKIPPED (could not read or not a data frame)\n")
    results[[i]] <- data.frame(
      dataset       = filename,
      n_variables   = NA,
      variable_list = "ERROR: could not read file",
      stringsAsFactors = FALSE
    )
  } else {
    vars <- names(df)
    cat(sprintf("%d variables\n", length(vars)))
    results[[i]] <- data.frame(
      dataset       = filename,
      n_variables   = length(vars),
      variable_list = paste(vars, collapse = "; "),
      stringsAsFactors = FALSE
    )
  }
}

# ---- Combine and write output ----
inventory <- do.call(rbind, results)

out_path <- file.path(data_dir, "variable_inventory.csv")
write.csv(inventory, file = out_path, row.names = FALSE)

cat(sprintf("\nDone. Inventory saved to:\n%s\n", out_path))
