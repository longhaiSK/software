# Install required packages
required_packages <- c("pak", "shiny", "httpuv")
for (pkg in required_packages) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    install.packages(pkg)
  }
}
if (!requireNamespace("shinylive", quietly = TRUE)) {
  pak::pak("posit-dev/r-shinylive")
}

# Load shinylive
library(shinylive)


# Define directories
input_dir <- "calcmark/"

cat("Original input_dir: ", input_dir, "\n")
# Remove an optional trailing forward slash or backslash
# Regex explanation:
# [/\\\\] : Character class matching either "/" or "\" (backslash needs \\\\ escaping)
# ?       : Makes the preceding match optional (zero or one time)
# $       : Anchors the match to the very end of the string
cleaned_input_dir <- sub("[/\\\\]?$", "", input_dir)
# Construct output_dir using the cleaned input
output_dir <- paste0(cleaned_input_dir, "_shiny")

cat("Cleaned input_dir:  ", cleaned_input_dir, "\n")
cat("Output_dir:       ", output_dir, "\n")

# Log R and package versions
cat("R version:", R.version.string, "\n")
cat("shinylive version:", as.character(packageVersion("shinylive")), "\n")

# Clean up old assets
# cat("Cleaning up old Shinylive assets...\n")
# #shinylive::assets_cleanup()
# 
# # Update assets
# cat("Downloading latest Shinylive assets...\n")
# shinylive::assets_download()

# Display asset information
cat("Current Shinylive assets:\n")
print(shinylive::assets_info())


# Verify input directory
if (!dir.exists(input_dir)) {
  stop("Input directory '", input_dir, "' does not exist.")
}

# Export with warning and error capture
cat("Exporting Shinylive app from", input_dir, "to", output_dir, "...\n")


shinylive::export(
  appdir = input_dir,
  destdir = output_dir,
  prefer_cran = TRUE,  # Default repository
  webr_timeout = 180,  # 3-minute timeout
  verbose = TRUE       # Detailed output
)

httpuv::runStaticServer(output_dir)


