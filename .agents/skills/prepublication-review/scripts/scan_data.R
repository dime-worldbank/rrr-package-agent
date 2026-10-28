# First-pass PII scan of every data file in a package (Part A, step 3).
# Usage: Rscript scripts/scan_data.R "<package root>" <out.txt> [max_mb_full_read=2000]
#
# For each file: dimensions, variables + labels, flagged variable names, every string column
# (unique count, MASKED examples, regex hits over ALL rows), large value-label sets, and
# a uniqueness check on common quasi-identifiers. Output is masked; never prints full values.
# Free text still has to be read by hand. This script only points you to where to look.

suppressMessages({ library(haven); library(readxl); library(data.table) })
args <- commandArgs(TRUE)
root <- args[1]; out <- args[2]
max_mb <- if (length(args) >= 3) as.numeric(args[3]) else 2000
sink(out, split = FALSE)

mask <- function(x) {
  x <- as.character(x)
  vapply(x, function(s) {
    if (is.na(s) || !nzchar(s)) return(s)
    s <- substr(s, 1, 60)
    paste(vapply(strsplit(s, " ", fixed = TRUE)[[1]], function(w)
      if (nchar(w) <= 1) w else paste0(substr(w, 1, 1), strrep("*", nchar(w) - 1)), ""), collapse = " ")
  }, "", USE.NAMES = FALSE)
}

pats <- c(
  email   = "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}",
  phone   = "(\\+?\\d{1,3}[ -]?)?\\(?\\d{2,4}\\)?[ -]?\\d{3,4}[ -]?\\d{3,4}\\b",
  url     = "https?://|www\\.",
  curp_mx = "\\b[A-Z]{4}\\d{6}[HM][A-Z]{5}[A-Z0-9]\\d\\b",
  rfc_mx  = "\\b[A-Z&]{3,4}\\d{6}[A-Z0-9]{3}\\b",
  cnic_pk = "\\b\\d{5}-\\d{7}-\\d\\b",
  aadhaar = "\\b\\d{4} ?\\d{4} ?\\d{4}\\b",
  ssn_us  = "\\b\\d{3}-\\d{2}-\\d{4}\\b",
  honor   = "\\b(Mr|Mrs|Ms|Miss|Dr|Sr|Sra|Srta|Don|Doña|Lic|Ing|Madam|Sir)\\.? [A-Z][a-z]+",
  namekw  = "(?i)\\b(my name is|name is|se llama|mi nombre|su nombre|nombre:)",
  address = "(?i)\\b(calle|avenida|av\\.|colonia|col\\.|street|st\\.|road|rd\\.|house no|casa no|manzana|lote|barrio)\\b"
)
flag_re <- "(?i)(name|nomb|apellido|phone|tel|cel|mobile|movil|whats|email|mail|correo|address|direcc|domicil|calle|village|aldea|locali|gps|lat|lon|coord|birth|dob|nacim|fecha_?nac|curp|rfc|nss|cnic|aadhaar|ssn|passport|national_?id|imei|sim|device|ip_?addr|ipaddress|recipient|firstname|lastname|school|escuela|clinic|enumer|interviewer|supervisor)"
free_re <- "(?i)(other|otro|otra|specify|especif|_os$|_oth|comment|coment|note|nota|remark|observ|reason|razon|descr|_txt|text|detalle)"

scan_df <- function(d, label) {
  cat("\n=====", label, "|", nrow(d), "rows x", ncol(d), "cols\n")
  for (v in names(d)) if (is.character(d[[v]])) d[[v]] <- iconv(d[[v]], "", "UTF-8", sub = "?")
  names(d) <- iconv(names(d), "", "UTF-8", sub = "?")
  if (!ncol(d)) return(invisible())
  for (v in names(d)) {
    x <- d[[v]]; lab <- attr(x, "label"); if (is.null(lab)) lab <- ""
    cls <- if (is.character(x)) "STR" else class(x)[1]
    cat(sprintf("  %-30s %-14s u=%-7d %s\n", v, cls, length(unique(x)), substr(lab, 1, 70)))
  }
  fl <- names(d)[grepl(flag_re, names(d), perl = TRUE) |
                   vapply(d, function(x) isTRUE(grepl(flag_re, paste0("", attr(x, "label")), perl = TRUE)), TRUE)]
  cat("  -- FLAGGED variable names/labels:", if (length(fl)) paste(fl, collapse = ", ") else "none", "\n")
  sv <- names(d)[vapply(d, is.character, TRUE)]
  cat("  -- string columns:", length(sv), "\n")
  for (v in sv) {
    x <- d[[v]]; x <- x[!is.na(x) & nzchar(trimws(x))]
    u <- unique(x)
    ft <- grepl(free_re, v, perl = TRUE) || (length(u) > 20 && mean(nchar(u)) > 25)
    cat(sprintf("  ## %s | non-empty=%d unique=%d meanlen=%.0f%s\n", v, length(x), length(u),
                if (length(u)) mean(nchar(u)) else 0, if (ft) " | FREE TEXT -> read by hand" else ""))
    if (length(u)) cat("     examples:", paste(mask(head(u, 8)), collapse = " | "), "\n")
    numlike <- grepl("^\\s*-?\\d*[.,]\\d+([eE][-+]?\\d+)?\\s*$|^\\s*-?\\d+([eE][-+]?\\d+)\\s*$", u, perl = TRUE)
    for (p in names(pats)) {
      h <- grepl(pats[[p]], u, perl = TRUE)
      if (p %in% c("phone", "aadhaar", "ssn_us", "cnic_pk")) {
        h <- h & !numlike  # skip plain decimals / sci notation
        # a numeric column read as text: skip bare integers (real phone columns are caught by the NUMERIC check below)
        if (mean(grepl("^\\s*-?[0-9.,eE+-]+\\s*$", u)) > 0.8) h <- h & !grepl("^\\s*-?\\d+\\s*$", u)
      }
      if (any(h)) cat(sprintf("     HIT %-8s %d unique values, e.g. %s\n", p, sum(h), paste(mask(head(u[h], 3)), collapse = " | ")))
    }
  }
  # numeric columns that look like phones / national IDs
  for (v in names(d)[vapply(d, is.numeric, TRUE)]) {
    x <- d[[v]]; x <- x[!is.na(x)]
    if (!length(x)) next
    xs <- x[seq_len(min(5000, length(x)))]
    nd <- nchar(format(abs(round(xs)), scientific = FALSE, trim = TRUE))
    if (all(xs == round(xs)) && (mean(nd == 10) > .5 || mean(nd %in% 11:13) > .5))
      cat(sprintf("  -- NUMERIC %s: most values have %s digits (phone/ID?) u=%d\n", v, names(sort(table(nd), TRUE))[1], length(unique(x))))
    if (grepl("(?i)lat|lon|gps|coord|^x$|^y$", v, perl = TRUE)) {
      dec <- nchar(sub("^[^.]*\\.?", "", format(x[seq_len(min(2000, length(x)))], scientific = FALSE, trim = TRUE)))
      cat(sprintf("  -- GPS? %s range [%.4f, %.4f] median decimals=%s\n", v, min(x), max(x), median(dec)))
    }
  }
  for (v in names(d)) {
    l <- attr(d[[v]], "labels")
    if (!is.null(l) && length(l) > 12) {
      hit <- grepl(paste(pats[c("email", "honor")], collapse = "|"), names(l), perl = TRUE, useBytes = TRUE)
      cat(sprintf("  -- VALUE LABELS %s: %d labels: %s%s\n", v, length(l), paste(mask(head(names(l), 6)), collapse = " | "),
                  if (any(hit)) sprintf("  [HIT %d]", sum(hit)) else ""))
    }
  }
  qi <- names(d)[grepl("(?i)^(age|edad|eda|sex|female|gender|sexo|marital|casado|married|educ|school|escuela|village|district|municip|ward|ent|state|region|cluster|ea|occup)", names(d), perl = TRUE)]
  if (length(qi) >= 2 && nrow(d) > 0) {
    qi <- qi[1:min(6, length(qi))]
    idv <- names(d)[grepl("(?i)^(id|folio\\w*|hhid|pid|caseid|uuid|key|respondent\\w*|anon_id|id_\\w+|\\w+_id)$", names(d), perl = TRUE)][1]
    dd <- if (!is.na(idv)) d[!duplicated(d[[idv]]), c(idv, qi), drop = FALSE] else d[, qi, drop = FALSE]
    k <- do.call(paste, c(lapply(qi, function(v) as.character(dd[[v]])), sep = "|"))
    t <- table(k)
    cat(sprintf("  -- QUASI-ID uniqueness on [%s]: %d of %d %s are unique\n", paste(qi, collapse = ", "), sum(t == 1), length(k),
                if (!is.na(idv)) paste0("units (first row per ", idv, ")") else "rows"))
  }
}

read_any <- function(f) {
  ext <- tolower(tools::file_ext(f)); mb <- file.size(f) / 1e6
  tryCatch({
    if (ext == "dta") {
      if (mb > max_mb) {
        nm <- names(read_dta(f, n_max = 0))
        list(main = read_dta(f, n_max = 200000), note = sprintf("LARGE (%.0f MB): first 200,000 rows only of %d cols", mb, length(nm)))
      } else list(main = read_dta(f))
    } else if (ext %in% c("sav", "por")) list(main = read_spss(f))
    else if (ext == "sas7bdat") list(main = read_sas(f))
    else if (ext %in% c("csv", "tsv", "txt")) {
      if (mb > max_mb) list(main = fread(f, colClasses = "character", showProgress = FALSE, fill = TRUE, nrows = 200000),
                            note = sprintf("LARGE (%.0f MB): first 200,000 rows only", mb))
      else list(main = fread(f, colClasses = "character", showProgress = FALSE, fill = TRUE))
    }
    else if (ext %in% c("xlsx", "xls", "xlsm")) setNames(lapply(excel_sheets(f), function(s) read_excel(f, sheet = s, col_types = "text")), excel_sheets(f))
    else if (ext == "rds") { o <- readRDS(f); if (is.data.frame(o)) list(main = o) else list(note = paste("rds object of class", class(o)[1])) }
    else if (ext %in% c("rdata", "rda")) { e <- new.env(); load(f, e); o <- mget(ls(e), e); o <- o[vapply(o, is.data.frame, TRUE)]; if (length(o)) o else list(note = "no data.frames inside") }
    else if (ext == "dbf") list(main = foreign::read.dbf(f, as.is = TRUE))
    else if (ext %in% c("gpkg", "geojson", "kml", "shp")) { o <- sf::st_drop_geometry(sf::st_read(f, quiet = TRUE)); list(main = as.data.frame(o)) }
    else if (ext == "json") { o <- jsonlite::fromJSON(f, flatten = TRUE); if (is.data.frame(o)) list(main = o) else list(note = "json not tabular, read by hand") }
    else list(note = "type not handled, read by hand")
  }, error = function(e) list(note = paste("COULD NOT OPEN:", conditionMessage(e))))
}

exts <- "\\.(dta|sav|por|sas7bdat|csv|tsv|xlsx|xls|xlsm|rds|rdata|rda|dbf|gpkg|geojson|kml|json)$"
fs <- list.files(root, pattern = exts, recursive = TRUE, full.names = TRUE, ignore.case = TRUE, all.files = TRUE)
fs <- fs[!grepl("/(ado|renv|\\.git)/|/node_modules/", fs)]
fs <- fs[!grepl("(data_hash_report|comparison_report|variable_inventory)\\.csv$", fs)]
txt <- list.files(root, pattern = "\\.txt$", recursive = TRUE, full.names = TRUE, ignore.case = TRUE)
txt <- txt[!grepl("/(ado|renv)/|LICENSE|RIDER|requirements", txt, ignore.case = TRUE) & file.size(txt) > 5000]
fs <- c(fs, txt)
cat("PII data scan of", root, "\n", length(fs), "data files\n", format(Sys.time()), "\n")
for (f in fs) {
  rel <- sub(paste0("^", gsub("([][{}()+*^$|\\\\?.])", "\\\\\\1", root), "/?"), "", f)
  r <- read_any(f)
  if (!is.null(r$note)) cat("\n=====", rel, "| NOTE:", r$note, "\n")
  for (nm in setdiff(names(r), "note")) if (is.data.frame(r[[nm]]))
    tryCatch(scan_df(as.data.frame(r[[nm]]), if (nm == "main") rel else paste0(rel, " [", nm, "]")),
             error = function(e) cat("\n  !! SCAN ERROR in", rel, nm, ":", conditionMessage(e), "-> check by hand\n"))
}
sink()
cat("wrote", out, "\n")
